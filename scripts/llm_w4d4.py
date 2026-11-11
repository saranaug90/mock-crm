"""Week 4, Day 4: approval for writes, least privilege, injection defence, audit log."""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC,datetime
from pathlib import Path

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam,ToolUseBlock,ToolResultBlockParam
from dotenv import load_dotenv

from types import SimpleNamespace

from llm_w4d2 import TOOLS, execute, text_of

MODEL = "claude-haiku-5-5"
CRM_URL = "http://127.0.0.1:8000"
MAX_ROUNDS = 6
AUDIT_FILE = Path("audit.jsonl")

SYSTEM = (
    "You are a support assistant for a CRM team, with tools to read and update tickets and customers. "
    "Use the tools to find facts; never guess IDs, names or values. "
    "Before changing a ticket, check its current state. "
    
    "Before any change runs, the user is shown it separately and asked to approve it. "
    "If a result says a change was declined, the user chose not to approve it at that step: "
    "don't make the change again; ask what they'd like instead. "
    "If a tool returns an error, explain it in plain words. "
    "Never mention tool names to the user. "
    "Keep answers short, because support leads are busy."
)

def is_write(tool_use: ToolUseBlock) -> bool:
    """True if this request is for a tool that changes data."""
    tool = TOOLS.get(tool_use.name)
    return tool is not None and tool.writes

def ask_human(summary: str) -> bool:
    """Ask the person at the keyboard to approve a change. Anything but 'y' means no."""
    return input(f"\n Approve? {summary} [y/N]").strip().lower() == "y"

def refuse(tool_use: ToolUseBlock, reason: str) -> ToolResultBlockParam:
    """A tool result saying the call did not run, and why."""
    return {"type": "tool_result","tool_use_id":tool_use.id, "content": reason, "is_error": True}

def audit(tool_use: ToolUseBlock, result: ToolResultBlockParam, approved: bool |None)-> None:
    """Append one line per tool call to the audit log."""
    entry = {
        "time": datetime.now(UTC).isoformat(),
        "tool": tool_use.name,
        "input": tool_use.input,
        "approved": approved,           # None for reads, which need no approval
        "error": result.get("is_error",False),
    }
    with AUDIT_FILE.open("a",encoding="utf-8") as f:
        f.write(json.dumps(entry)+"\n")

async def run_tools(
        crm: httpx.AsyncClient,
        tool_uses: list[ToolUseBlock],
        allow_writes: bool,
        approve: callable[[str],bool],
        ) -> list[ToolResultBlockParam]:
    """Run reads concurrently; run writes one at a time, only if permitted and approved."""
    results: dict[str,ToolResultBlockParam] = {}

    reads = [t for t in tool_uses if not is_write(t)]
    for t, r in zip(reads, await asyncio.gather(*(execute(crm,t) for t in reads))):
        results[t.id] = r
        audit(t, r, approved = None)

    writes = [t for t in tool_uses if is_write(t)]
    for t in writes:
        if not allow_writes:
            results[t.id] = refuse(t, "This assistant is read-only and cannot make changes.")
            audit(t,results[t.id],approved = False)
            continue
        approved = approve(f"{t.name} {json.dumps(t.input)}")
        if approved:
            results[t.id] = await execute(crm,t)
        else:
            results[t.id] = refuse(t, "Not done: the user was shown this change and chose not to approve it.")
        audit(t, results[t.id], approved= approved)

    return [results[t.id] for t in tool_uses]

async def run_agent(
        llm: AsyncAnthropic,
        crm: httpx.AsyncClient,
        messages: list[MessageParam],
        allow_writes: bool = True,
        approve: Callable[[str],bool] = ask_human,
) ->str:
    """The Day 3 agent loop, with permission checks and approval for writes."""
    tools = [t.to_param() for t in TOOLS.values() if allow_writes or not t.writes]

    for round_number in range(1,MAX_ROUNDS+1):
        response = await llm.messages.create(
            model = MODEL, max_tokens=1000, system= SYSTEM, tools=tools, messages=messages
        )
        messages.append({"role":"assistant","content":response.content})
        if response.stop_reason != "tool_use":
            return text_of(response) or "Sorry, I couldn't produce an answer."

        tool_uses = [b for b in response.content if isinstance(b,ToolUseBlock)]
        for t in tool_uses:
            print(f"[round {round_number}] ->{t.name} {t.input}")
        messages.append({"role": "user", "content": await run_tools(crm, tool_uses, allow_writes, approve)})
    return "Sorry, that needed too many steps. Please try a narrower question."


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
    asyncio.run(chat(allow_writes=False))
        


