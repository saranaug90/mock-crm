"""Week 4, Day 3: the agent loop."""

import asyncio

import httpx
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, ToolUseBlock
from dotenv import load_dotenv

from llm_w4d2 import TOOLS, execute, text_of

MODEL = "claude-haiku-5-5"
CRM_URL = "http://127.0.0.1:8000"
MAX_ROUNDS = 6

SYSTEM = (
    "You are a support assistant for a CRM team, with tools to read and update tickets and customers. "
    "Use the tools to find facts; never guess IDs, names or values. "
    "Before changing a ticket, check its current state. "
    "If a tool returns an error, explain it to the user in plain words. "
    "Keep answers short, because support leads are busy. "
    "Never mention tool names to the user. "
)
    

LIMIT_NOTE = (
    "\n\nThe step limit for the current request has been reached. Answer now without tools, "
    "using only the information above. Say what you couldn't check and suggest a follow-up "
    "question the user can ask. Never mention tool names."
   
)

async def run_agent(llm: AsyncAnthropic, crm: httpx.AsyncClient, messages: list[MessageParam]) -> str:
    """Call the model and run its tool requests until it gives a final answer."""
    tools = [tool.to_param() for tool in TOOLS.values()]
    input_tokens = 0
    output_tokens = 0

    for round_number in range(1, MAX_ROUNDS + 1):
        response = await llm.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM, tools=tools, messages=messages
        )
        messages.append({"role": "assistant", "content": response.content})

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        print("input_token: ",input_tokens)
        print("output_token: ",output_tokens)

        if response.stop_reason != "tool_use":
            return text_of(response)                     # finished: the model answered

        tool_uses = [b for b in response.content if isinstance(b, ToolUseBlock)]
        for t in tool_uses:
            print(f"  [round {round_number}] → {t.name}({t.input})")
        results = await asyncio.gather(*(execute(crm, t) for t in tool_uses))
        messages.append({"role": "user", "content": list(results)})

    # Out of rounds: add the note at the END of a copy (after every signed block), system unchanged
    last = messages[-1]
    final_messages: list[MessageParam] = [
        *messages[:-1],
        {"role": "user", "content": [*last["content"], {"type": "text", "text": LIMIT_NOTE}]},
    ]
    response = await llm.messages.create(
        model=MODEL, max_tokens=1000, system=SYSTEM, tools=tools,
        tool_choice={"type": "none"}, messages=final_messages,
    )
    answer = text_of(response) or "Sorry, I couldn't finish that request. Please try a narrower question."
    messages.append({"role": "assistant", "content": answer})    # plain text: its blocks were signed with the note
    return answer

async def chat() -> None:
    """A simple command-line chat with the CRM assistant."""
    load_dotenv()
    llm = AsyncAnthropic()
    messages: list[MessageParam] = []
    async with httpx.AsyncClient(base_url=CRM_URL, timeout=5.0) as crm:
        while True:
            question = input("\nYou: ").strip()
            if question.lower() in {"", "quit", "exit"}:
                break
            messages.append({"role": "user", "content": question})
            answer = await run_agent(llm, crm, messages)
            print(f"Assistant: {answer}")


if __name__ == "__main__":
    asyncio.run(chat())