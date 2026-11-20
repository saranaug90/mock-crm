"""A first call to the Claude API."""

import asyncio

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message
from dotenv import load_dotenv

MODEL = "claude-haiku-5-5"


async def call_llm(
    client: AsyncAnthropic, question: str, max_token: int = 300
) -> Message:
    """Send one question to the model and return the message object in its reply."""
    message = await client.messages.create(
        model=MODEL,
        max_tokens=max_token,
        messages=[{"role": "user", "content": question}],
    )
    return message


def text_of(message: Message) -> str:
    return "".join(block.text for block in message.content if block.type == "text")


INPUT_USD_PER_MTOK = 0.10  # Haiku 5.5 starting price, per million input tokens
OUTPUT_USD_PER_MTOK = 0.50  # per million output tokens


def cost_usd(message: Message) -> float:
    """Estimate the cost of one call in US dollars."""
    return (
        message.usage.input_tokens * INPUT_USD_PER_MTOK
        + message.usage.output_tokens * OUTPUT_USD_PER_MTOK
    ) / 1_000_000


async def main() -> None:
    load_dotenv()
    client = AsyncAnthropic()
    question = "In two sentences, what is a CRM system?"
    try:
        messages = await asyncio.gather(
            call_llm(client, question),
            call_llm(client, question),
            call_llm(client, question),
        )
        for i, message in enumerate(messages, start=1):
            print(f"---------Answer {i}----------")
            print(text_of(message))
            print("Stop Reason:", message.stop_reason)
            print(
                "Tokens: ",
                message.usage.input_tokens,
                "in",
                message.usage.output_tokens,
                "out",
            )
            print(f"Cost:  {cost_usd(message):.6f}")
    except anthropic.AuthenticationError as e:
        print(type(e).__name__, e.status_code)


asyncio.run(main())
