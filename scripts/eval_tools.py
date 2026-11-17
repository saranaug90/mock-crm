"""Week 4, Day 5: an eval. Does the real model pick the right first tool?"""

import asyncio
from anthropic import AsyncAnthropic
from anthropic.types import ToolUseBlock
from dotenv import load_dotenv

from llm_w4d2 import TOOLS
from llm_w4d4 import MODEL,SYSTEM

CASES = [
    ("What's the status of T-2?",          "get_ticket"),
    ("Who is customer C-2?",               "get_customer"),
    ("Which open tickets are urgent?",     "search_tickets"),
    ("How much has C-1 spent in total?",   "get_customer_total"),
    ("How many tickets does C-1 has in total", "get_customer_summary"),
    ("Does T-1 have assignee?", "get_ticket"),
    ("Does C-1 has any high priority open tickets?", "get_customer_summary"),
    ("What does ticket priority mean?",    None),              # None = no tool should be used
]

async def first_tool(llm: AsyncAnthropic, question: str) -> str | None:
    """Ask the model once, and return the name of the first tool it asks for (or None)."""
    tools = [t.to_param() for t in TOOLS.values()]
    response = await llm.messages.create(model=MODEL, max_tokens=1000, system=SYSTEM, tools=tools, messages =[{"role":"user","content":question}])
    for block in response.content:
        if isinstance(block,ToolUseBlock):
            return block.name
    return None

async def main() -> None:
    load_dotenv()
    llm = AsyncAnthropic()
    picked = await asyncio.gather(*(first_tool(llm,question) for question, _ in CASES))

    correct = 0
    for (question,expected),got in zip(CASES,picked):
        if got == expected:
            correct +=1
        else:
            print(f"MISS: {question!r}: expected {expected}, got {got}")
    print(f"Accuracy: {correct}/{len(CASES)}")

if __name__ =="__main__":
    asyncio.run(main())

