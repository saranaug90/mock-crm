"""Command-line chat with the CRM assistant."""

import asyncio

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

from mock_crm.agent.loop import run_agent

CRM_URL = "http://127.0.0.1:8000"


async def chat(allow_writes: bool = True) -> None:
    """Command-line chat with the CRM assistant."""
    load_dotenv()
    llm = AsyncAnthropic()
    messages: list[MessageParam] = []
    async with httpx.AsyncClient(base_url=CRM_URL, timeout=5.0) as crm:
        while True:
            question = input("\nYou: ").strip()
            if question.lower() in {"", "quit", "exit"}:
                break
            messages.append({"role": "user", "content": question})
            print(f"Assistant: {await run_agent(llm, crm, messages, allow_writes)}")


if __name__ == "__main__":
    asyncio.run(chat())
