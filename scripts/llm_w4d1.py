"""Week 4, Day 1: tool use, step by step."""

import asyncio
import json
from typing import Any

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam, ToolParam, ToolUseBlock
from dotenv import load_dotenv
from pydantic import BaseModel

MODEL = "claude-haiku-5-5"
CRM_URL = "http://127.0.0.1:8000"
DESCRIPTION = (
    "Fetch one support ticket from the CRM by its ID, such as 'T-1'. "
    "Returns the ticket's customer, status, priority (1 = low, 5 = urgent) and assignee. "
    "Use this whenever the user asks about a specific ticket."
)

GET_TICKET_TOOL: ToolParam = {
    "name": "get_ticket",
    "description": DESCRIPTION,
    "input_schema": {
        "type": "object",
        "properties": {
            "ticket_id": {
                "type": "string",
                "description": "The ticket ID, for example 'T-1'",
            },
        },
        "required": ["ticket_id"],
    },
}


class GetTicketInput(BaseModel):
    """Arguments the model must provide to get_ticket."""

    ticket_id: str


async def get_ticket(crm: httpx.AsyncClient, ticket_id: str) -> dict[str, Any]:
    """Fetch one ticket from the CRM API."""
    response = await crm.get(f"/tickets/{ticket_id}")
    response.raise_for_status()
    return response.json()


def text_of(message: Message) -> str:
    """Join the text of all text blocks in a response."""
    return "".join(block.text for block in message.content if block.type == "text")


async def main() -> None:
    load_dotenv()
    llm = AsyncAnthropic()
    question = "What’s the status of ticket T-1, and who is working on it?"
    messages: list[MessageParam] = [{"role": "user", "content": question}]

    # Step 1: ask, offering the tool
    response = await llm.messages.create(
        model=MODEL, max_tokens=1000, tools=[GET_TICKET_TOOL], messages=messages
    )
    print("Stop reason:", response.stop_reason)
    for block in response.content:
        print(" ", block.type, block)

    if response.stop_reason == "tool_use":
        # Step 2: find the model's request and run the tool
        tool_use = next(b for b in response.content if isinstance(b, ToolUseBlock))
        args = GetTicketInput.model_validate(tool_use.input)
        async with httpx.AsyncClient(base_url=CRM_URL, timeout=5.0) as crm:
            try:
                ticket = await get_ticket(crm, args.ticket_id)
                content = json.dumps(ticket)
                is_error = False
            except httpx.HTTPStatusError as e:
                content = f"CRM returned {e.response.status_code}: {e.response.text}"
                is_error = True
            except httpx.RequestError as e:
                content = (
                    f"The CRM could not be reached ({type(e).__name__}). "
                    "Do not retry. Tell the user the CRM is unavailable and to try again later."
                )
                is_error = True
        print("Tool returned:", content)

        # Step 3: send back the model's own turn, then the result
        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": content,
                        "is_error": is_error,
                    },
                ],
            }
        )

        # Step 4: the model answers using the result
        final = await llm.messages.create(
            model=MODEL, max_tokens=1000, tools=[GET_TICKET_TOOL], messages=messages
        )
        print("Stop reason:", final.stop_reason)
        print(text_of(final))
    else:
        print(text_of(response))


if __name__ == "__main__":
    asyncio.run(main())
