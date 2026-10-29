"""Week 3, Day 2: system prompts, conversations, and parameters."""

import asyncio

from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam
from dotenv import load_dotenv

MODEL = "claude-haiku-5-5"

SUPPORT_PROMPT = (
    "You are a support assistant for a CRM system. "
    "Answer in at most two sentences. "
    "If a question is not about customers, tickets, or orders, "
    "politely say you can only help with CRM topics."
)

messages = [
    {"role": "user", "content": "Hello, Claude"},
    {"role": "assistant", "content": "Hello!"},
    {"role": "user", "content": "Can you describe LLMs to me?"},
]


def text_of(message: Message) -> str:
    """Join the text of all text blocks in a response."""
    return "".join(block.text for block in message.content if block.type == "text")


async def chat(
    client: AsyncAnthropic, history: list[MessageParam], user_text: str
) -> str:
    """Add the user's turn, get a reply, add the reply to history, and return it."""
    history.append({"role": "user", "content": user_text})
    message = await client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=SUPPORT_PROMPT,
        messages=history,
    )
    reply = text_of(message)
    history.append({"role": "assistant", "content": reply})
    print(
        f"[tokens: {message.usage.input_tokens} in, {message.usage.output_tokens} out]"
    )
    return reply


async def main() -> None:
    load_dotenv()
    client = AsyncAnthropic()
    history: list[MessageParam] = []
    print("CRM assistant. Type 'quit' to stop.")
    while True:
        user_text = input("You: ").strip()
        if user_text.lower() == "quit":
            break
        if not user_text:
            continue
        reply = await chat(client, history, user_text)
        print(f"Assistant: {reply}\n")


asyncio.run(main())
