"""Incoming Customer Messages are triaged and the tickets are created at CRM"""

import asyncio
from collections import Counter

import httpx
from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from llm_day5 import triage_many

BASE_URL = "http://127.0.0.1:8000"

INBOX = [
    ("C-1", "My card was charged but the order shows unpaid."),
    ("C-2", "I can't log in after resetting my password."),
    ("C-1", "The dashboard takes two minutes to load."),
    ("C-3", "Login page is not loading. I need to make payment today.Its urgent"),
    ("C-1", "Why is there a late fee on this month's invoice?"),
    ("C-2", "Please add my colleague as a second user."),
    ("C-3", "Uploading a CSV file freezes the page."),
    ("C-4", "Is it going to rain over this weekend?"),
]


async def main() -> None:
    load_dotenv()
    llm = AsyncAnthropic()
    ticket_with_triage = []  # To hold the triage details from llm and to ticket details from CRM
    ignored = []  # to hold the "other" requests, which can be ignored

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5.0) as crm:
        try:
            (await crm.get("/health")).raise_for_status()
        except httpx.HTTPError as e:
            print(f"CRM is not available ({type(e).__name__}); nothing processed.")
            return
        messages = [msg for _, msg in INBOX]
        triage_result = await triage_many(llm, messages, limit=4)
        for (customer, _), result in zip(INBOX, triage_result):
            if result is None:
                continue
            # Decision: messages triaged as "other" are not support requests, so no ticket is created.
            if result.queue == "other":
                ignored.append(customer)
                continue
            try:
                response = await crm.post(
                    "/tickets", json={"customer": customer, "priority": result.priority}
                )
                response.raise_for_status()
                # Decision: the CRM API only accepts customer and priority today, so queue, summary
                # and needs_human are kept in this script's report only. Storing them would need new
                # Ticket fields in the API (future work).
                ticket = result.model_dump() | response.json()
                ticket_with_triage.append(ticket)
            except httpx.HTTPStatusError as e:
                print(
                    f"CRM rejected ticket for {customer}: {e.response.status_code} {e.response.text}"
                )
            except httpx.RequestError as e:
                print("Exception :", type(e).__name__, e)
    triage_failed = sum(1 for r in triage_result if r is None)
    api_failed = len(INBOX) - triage_failed - len(ignored) - len(ticket_with_triage)
    print(
        f"Report: processed {len(INBOX)} message(s): {len(ticket_with_triage)} ticket(s) created, {triage_failed} triage failures, {api_failed} API failure, {len(ignored)} ignored"
    )
    by_queue = Counter(ticket["queue"] for ticket in ticket_with_triage)
    print("By queue:", ", ".join(f"{q} {n}" for q, n in by_queue.most_common()))
    needs_human_review = [
        ticket["id"] for ticket in ticket_with_triage if ticket["needs_human"]
    ]
    print(f"Needs human review: {needs_human_review}")


asyncio.run(main())
