"""Week 3, Day 2 exercises."""

import asyncio

import anthropic
from anthropic import AsyncAnthropic
from anthropic.types import Message, MessageParam
from dotenv import load_dotenv

MODEL = "claude-haiku-5-5"

SUPPORT_PROMPT = (
        "You are a support assistant for a CRM system. "
        "Answer it in the format Answer: <one sentence>. "
        "Ticket priority runs from 1 (low) to 5 (urgent). "
        "If a question is not about customers, tickets, or orders, "
        "politely say you can only help with CRM topics."
    )

def text_of(message: Message) -> str:
    """Join the text of all text blocks in a response."""
    return "".join(block.text for block in message.content if block.type == "text")

async def chat(client: AsyncAnthropic,messages: list[MessageParam],support_prompt: str = "") -> Message:
    message = await client.messages.create(
            model=MODEL,
            max_tokens=300,
            system = support_prompt,
            messages=messages
        )
    return message
# System prompt design: write a system prompt for a CRM assistant that replies only in the form Answer: <one sentence>. 
# Test it with three questions, including an off-topic one. How reliably does the model follow the format?

async def exercise_1(client: AsyncAnthropic) -> None:
    """System prompt that forces 'Answer: <one sentence>'."""
    
    for question in ["What does ticket priority 5 mean?","Customer C-1 has two open tickets: T-1 (priority 3) and T-3 (priority 5).","What's a good pasta recipe?"]:
        message = [{"role":"user","content":question}]
        reply = await chat(client,message, SUPPORT_PROMPT)
        print(f"Q: {question}: A:{text_of(reply)}")
        print("stop:", reply.stop_reason, "| blocks:", [block.type for block in reply.content])

        #observation: all three replies starts with Answer:  and the off-topic is replied with can help with CRM topics only message

# Proving statelessness: in one call, send “My name is Saranya.” In a separate call with a fresh history, 
# ask “What’s my name?” Then do it again with both turns in one history. Print both answers. What does this prove?
async def exercise_2(client: AsyncAnthropic) -> None:
    """Prove the API is stateless."""
    # reply = await chat(client,[{"role":"user", "content":"My name is Saranya"}])
    # print(text_of(reply))
    # reply = await chat(client,[{"role":"user", "content":"what is my name?"}])
    # print(text_of(reply))
    history: list[MessageParam] = []
    history.append({"role":"user", "content":"My name is Saranya"})
    first_reply = await chat(client,[{"role":"user", "content":"My name is Saranya"}])
    history.append({"role":"assistant","content":text_of(first_reply)})
    history.append({"role":"user", "content":"what is my name?"})
    second_reply = await chat(client,history)
    print(text_of(second_reply))
    
    # llm reply is Your name is Saranya, as you told me in your first message. API calls are stateless, we have to include the history in all the messages to make llm remember it.


async def exercise_3(client: AsyncAnthropic) -> None:
    """Record input tokens across a three-turn conversation."""
    SUPPORT_PROMPT = (
        "You are a support assistant for a CRM system. "
        "Answer it in th format Answer: <one sentence>. "
        "If a question is not about customers, tickets, or orders, "
        "politely say you can only help with CRM topics."
       )
    history: list[MessageParam] =[]
    for question in ["What does ticket priority 5 mean?","Customer C-1 has two open tickets: T-1 (priority 3) and T-3 (priority 5).","What's a good pasta recipe?"]:
        message = {"role":"user","content":question}
        history.append(message)
        reply = await chat(client,history, SUPPORT_PROMPT)
        history.append({"role":"assistant","content":text_of(reply)})
        print(f"[tokens: {reply.usage.input_tokens} in, {reply.usage.output_tokens} out]")
   
        #observation: in tokens are increaed for every turn
   


async def exercise_4(client: AsyncAnthropic) -> None:
    """Catch the temperature error."""
    try:
        message = await client.messages.create(
            model=MODEL,
            max_tokens=300,
            temperature = 0.5,
            messages=[{"role":"user","content":"my name is saranya"}]
        )
    except TypeError as e:
        print(f"Error: {e}")

async def main() -> None:
    load_dotenv()
    client = AsyncAnthropic()
    await exercise_1(client)
    await exercise_2(client)
    await exercise_3(client)
    await exercise_4(client)


asyncio.run(main())