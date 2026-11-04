"""Week 4, Day 2: several tools on the CRM API, with schemas from Pydantic."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import (
    Message,
    MessageParam,
    ToolParam,
    ToolResultBlockParam,
    ToolUseBlock,
)
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

MODEL = "claude-haiku-5-5"
CRM_URL = "http://127.0.0.1:8000"

Status = Literal["open", "closed", "pending"]
TICKET_ID = Field(pattern=r"^T-\d+$", description="Ticket ID, for example 'T-1'")
CUSTOMER_ID = Field(pattern=r"^C-\d+$", description="Customer ID, for example 'C-1'")


# ---- Tool inputs ----

class GetTicketInput(BaseModel):
    ticket_id: str = TICKET_ID


class SearchTicketsInput(BaseModel):
    status: Status | None = Field(default=None, description="Only tickets with this status")
    min_priority: int | None = Field(
        default=None, ge=1, le=5, description="Only tickets at or above this priority (1 = low, 5 = urgent)"
    )


class GetCustomerInput(BaseModel):
    customer_id: str = CUSTOMER_ID


class UpdateTicketInput(BaseModel):
    ticket_id: str = TICKET_ID
    status: Status | None = Field(default=None, description="New status, if changing it")
    assignee: str | None = Field(default=None, description="Person to assign, if changing it")

class GetCustomerTotalInput(BaseModel):
    customer_id: str = CUSTOMER_ID


# ---- Tool code: each one calls the CRM ----

async def run_get_ticket(crm: httpx.AsyncClient, args: GetTicketInput) -> Any:
    response = await crm.get(f"/tickets/{args.ticket_id}")
    response.raise_for_status()
    return response.json()


async def run_search_tickets(crm: httpx.AsyncClient, args: SearchTicketsInput) -> Any:
    response = await crm.get("/tickets", params=args.model_dump(exclude_none=True))
    response.raise_for_status()
    return response.json()


async def run_get_customer(crm: httpx.AsyncClient, args: GetCustomerInput) -> Any:
    response = await crm.get(f"/customers/{args.customer_id}")
    response.raise_for_status()
    return response.json()


async def run_update_ticket(crm: httpx.AsyncClient, args: UpdateTicketInput) -> Any:
    changes = args.model_dump(exclude_none=True, exclude={"ticket_id"})
    response = await crm.patch(f"/tickets/{args.ticket_id}", json=changes)
    response.raise_for_status()
    return response.json()

async def run_get_customer_total(crm: httpx.AsyncClient, args: GetCustomerTotalInput)-> Any:
    response = await crm.get(f"/customers/{args.customer_id}/total")
    response.raise_for_status()
    return response.json()

@dataclass
class Tool:
    """One tool: what the model sees, and the code that runs it."""
    name: str
    description: str
    input_model: type[BaseModel]
    run: Callable[[httpx.AsyncClient, Any], Awaitable[Any]]

    def to_param(self) -> ToolParam:
        """The definition sent to the model, with the schema generated from the input model."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_model.model_json_schema(),
        }


TOOLS: dict[str, Tool] = {
    tool.name: tool
    for tool in [
        Tool("get_ticket",
             "Fetch one support ticket by ID. Returns its customer, status, priority "
             "(1 = low, 5 = urgent) and assignee. Use when the user names a specific ticket.",
             GetTicketInput, run_get_ticket),
        Tool("search_tickets",
             "Find ticket IDs by status and/or minimum priority. Returns a list of IDs only; "
             "use get_ticket for details.",
             SearchTicketsInput, run_search_tickets),
        Tool("get_customer",
             "Fetch one customer's record by customer ID, such as 'C-1'.",
             GetCustomerInput, run_get_customer),
        Tool("update_ticket",
             "Change a ticket's status and/or assignee. Business rule: a ticket can only be "
             "closed if it has an assignee. Returns the updated ticket.",
             UpdateTicketInput, run_update_ticket),
        Tool("get_customer_total",
             "Returns the sum of all the customer’s order totals, in USD",
             GetCustomerTotalInput,run_get_customer_total)
    ]
}
async def execute(crm: httpx.AsyncClient, tool_use: ToolUseBlock) -> ToolResultBlockParam:
    """Run one tool request and return its result block, never raising."""
    def result(content: str, is_error: bool = False) -> ToolResultBlockParam:
        return {"type": "tool_result", "tool_use_id": tool_use.id, "content": content, "is_error": is_error}

    tool = TOOLS.get(tool_use.name)
    if tool is None:
        return result(f"Unknown tool: {tool_use.name}", is_error=True)
    try:
        args = tool.input_model.model_validate(tool_use.input)
    except ValidationError as e:
        return result(f"Invalid arguments: {e}", is_error=True)       # the CRM is never called
    try:
        return result(json.dumps(await tool.run(crm, args)))
    except httpx.HTTPStatusError as e:
        return result(f"CRM returned {e.response.status_code}: {e.response.text}", is_error=True)
    except httpx.RequestError as e:
        return result(f"The CRM could not be reached ({type(e).__name__}). Do not retry; "
                      "tell the user the CRM is unavailable.", is_error=True)

def text_of(message: Message) -> str:
    return "".join(block.text for block in message.content if block.type == "text")


async def ask(llm: AsyncAnthropic, crm: httpx.AsyncClient, question: str) -> None:
    """One round: question → tool requests → results → answer."""
    tools = [tool.to_param() for tool in TOOLS.values()]
    messages: list[MessageParam] = [{"role": "user", "content": question}]

    response = await llm.messages.create(model=MODEL, max_tokens=1000, tools=tools, messages=messages)
    tool_uses = [b for b in response.content if isinstance(b, ToolUseBlock)]
    for t in tool_uses:
        print(f"  → {t.name}({t.input})")

    if response.stop_reason == "tool_use":
        results = [await execute(crm, t) for t in tool_uses]
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": results})
        response = await llm.messages.create(model=MODEL, max_tokens=1000, tools=tools, messages=messages)
        if response.stop_reason == "tool_use":
            print("  (the model wants another round; the Day 3 loop will handle that)")

    print(text_of(response))


async def main() -> None:
    load_dotenv()
    llm = AsyncAnthropic()
    async with httpx.AsyncClient(base_url=CRM_URL, timeout=5.0) as crm:
        await ask(llm, crm, "Show the total spent for C-1.")


if __name__ == "__main__":
    asyncio.run(main())