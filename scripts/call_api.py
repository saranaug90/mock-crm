"""Call the running mock CRM service from Python."""

import asyncio

import httpx

from mock_crm.models import Ticket

BASE_URL = "http://127.0.0.1:8000"


async def fetch_ticket(client: httpx.AsyncClient, ticket_id: str) -> Ticket | None:
    response = await client.get(f"/tickets/{ticket_id}")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    ticket = Ticket.model_validate(response.json())
    return ticket


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=5.0) as client:
        try:
            # response = await client.get("/health")
            # print(response.status_code, response.json())

            # response = await client.get("/tickets/T-3")
            # ticket = Ticket.model_validate(response.json())
            # print(ticket)

            # response = await client.get("/tickets", params={"status": "open", "min_priority": 4})
            # print(response.status_code, response.json())

            # response = await client.post("/tickets", json={"customer": "C-2", "priority": 4})
            # print(response.status_code, response.json())

            # response = await client.patch("/tickets/T-1", json={"status": "pending"})
            # print(response.status_code, response.json())

            # response = await client.get("/tickets/T-99")
            # if response.status_code == 404:
            #     print("Not found", response.json()["detail"])

            # response = await client.get("/tickets/T-99")
            # try:
            #     response.raise_for_status()
            # except httpx.HTTPStatusError as e:
            #     print("Exception", e.response.json()["detail"])
            result = await asyncio.gather(
                fetch_ticket(client, "T-3"), fetch_ticket(client, "T-99")
            )
            print(result)

        except httpx.RequestError as e:
            print("Exception :", type(e).__name__, e)


asyncio.run(main())
