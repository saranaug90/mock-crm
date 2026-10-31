"""Week 3, Day 5: concurrency limits, streaming, and API errors."""

import asyncio
import time

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message
from dotenv import load_dotenv
from llm_day4 import TicketTriage, triage

MODEL = "claude-haiku-5-5"


TEST_CASES = [
    ("My card was charged but the order shows unpaid.", "billing"),
    ("I can't log in after resetting my password.", "account"),
    ("The dashboard takes two minutes to load.", "technical"),
    ("Why is there a late fee on this month's invoice?", "billing"),
    ("Please add my colleague as a second user.", "account"),
    ("Uploading a CSV file freezes the page.", "technical"),
]


def text_of(message: Message) -> str:
    """Join the text of all text blocks in a response."""
    return "".join(block.text for block in message.content if block.type == "text")


async def summarize(client: AsyncAnthropic, sem: asyncio.Semaphore, text: str) -> str:
    """Summarize one text, waiting for a free slot first."""
    async with sem:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=200,
            messages=[
                {"role": "user", "content": f"Summarize in one sentence: {text}"}
            ],
        )
    return text_of(response)


async def summarize_all(
    client: AsyncAnthropic, texts: list[str], limit: int = 3
) -> list[str]:
    """Summarize every text, with at most `limit` calls running at once."""
    sem = asyncio.Semaphore(limit)
    return await asyncio.gather(*(summarize(client, sem, t) for t in texts))


async def stream_reply(
    client: AsyncAnthropic, prompt: str, max_tokens: int = 500
) -> None:
    """Print the reply as it arrives, then show the usage."""
    async with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
        final = await stream.get_final_message()

    print()
    print(
        f"Stop reason: {final.stop_reason}, output tokens: {final.usage.output_tokens}"
    )


async def make_error(client: AsyncAnthropic, model: str = MODEL) -> None:
    try:
        await client.messages.create(
            model=model,
            max_tokens=300,
            messages=[{"role": "user", "content": "say hi"}],
        )
    except anthropic.APIError as e:
        print("Exception Type:", type(e).__name__)
        print(getattr(e, "status_code", None))


def apply_business_rules(result: TicketTriage) -> TicketTriage:
    """Enforce rules that follow mechanically from other fields."""
    if result.priority >= 4:
        result.needs_human = True
    return result


async def safe_triage(
    client: AsyncAnthropic, message: str, sem: asyncio.Semaphore
) -> TicketTriage | None:
    async with sem:
        try:
            result = await triage(client, message)
            return apply_business_rules(result)
        except anthropic.APIError as e:
            print(f"API error for {message!r}:{type(e).__name__}")
        except ValueError as e:
            print(f"No usable output for {message!r}: {e}")
    return None


async def triage_many(
    client: AsyncAnthropic, messages: list[str], limit: int = 3
) -> list[TicketTriage | None]:
    sem = asyncio.Semaphore(limit)
    return await asyncio.gather(*(safe_triage(client, msg, sem) for msg in messages))


async def main() -> None:
    load_dotenv()
    client = AsyncAnthropic()
    # E 1 Make a list of 6 short texts (reuse some of your TEST_CASES messages). Time summarize_all with limit=1, limit=3 and limit=6:
    # A limit 1 will allocate only one space, so 6 text will run one after another- - 6 times. limit 3 will allocate 3 spaces, so 3 cases run at 2 times.limit 6 will allocate 6 spaces,
    # which will make 6 calls at the same time. so limit 1 time will be almost near 6 times of limit 6 time.
    text = [msg for msg, _ in TEST_CASES]
    start = time.perf_counter()
    await summarize_all(client, text, limit=1)
    print(f"limit=1: {time.perf_counter() - start:.1f}s")
    start = time.perf_counter()
    await summarize_all(client, text, limit=3)
    print(f"limit=3: {time.perf_counter() - start:.1f}s")
    start = time.perf_counter()
    await summarize_all(client, text, limit=6)
    print(f"limit=6: {time.perf_counter() - start:.1f}s")
    # E 2 Call stream_reply with “Explain in about 150 words what a support triage queue is.” Watch it appear.
    # Then run it again with max_tokens=20.
    # What’s the stop_reason, and what happened to the text?
    # A 1st reply: Stop reason: end_turn, output tokens: 291 there was a complete explanation and 2nd reply Stop reason: max_tokens, output tokens: 20 and the explanation is incomplete
    prompt = "Explain in about 150 words what a support triage queue is."
    await stream_reply(client, prompt)
    await stream_reply(client, prompt, max_tokens=20)
    # E 3 Exercise 3: trigger three errors on purpose.
    # Write a small function that makes one call inside try/except anthropic.APIError as e: and prints type(e).__name__ and getattr(e, "status_code", None). Trigger each of these errors:

    # a model name that doesn’t exist, e.g. "claude-nope"    # A Exception Type: NotFoundError 404
    # a wrong key: AsyncAnthropic(api_key="wrong-key") (a fake key in code is fine; never paste your real one) # Exception Type: AuthenticationError 401
    # client.with_options(timeout=0.01, max_retries=0)   # A Exception Type: APITimeoutError None
    # None of these are worth retry, since all the exceptions are due to parameters that we used to connect with the model.
    impatient = client.with_options(timeout=0.01, max_retries=0)
    await make_error(client, "claude-nope")
    await make_error(AsyncAnthropic(api_key="wrong-key"))
    await make_error(impatient)
    # E 4 Write triage_many(client, messages, limit=3) -> list[TicketTriage | None] that uses your Day 4 triage() with a semaphore and error handling, so one failure doesn’t stop the others.
    messages = [message for message, _ in TEST_CASES]
    result = await triage_many(client, messages, limit=6)
    print(result)
    result = await triage_many(impatient, messages, limit=6)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
