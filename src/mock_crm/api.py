"""HTTP API for the Mock CRM."""

from fastapi import FastAPI, HTTPException
from pydantic import ValidationError

from mock_crm.errors import format_errors
from mock_crm.models import (
    Customer,
    CustomerSummary,
    CustomerTotal,
    Order,
    Status,
    Ticket,
    TicketCreate,
    TicketUpdate,
)
from mock_crm.services import (
    create_ticket,
    customer_order_total,
    find_tickets,
    get_customer,
    get_ticket,
    orders_by_customer,
    summarize_customer,
    update_ticket,
)

app = FastAPI(
    title="Mock CRM", description="A Mock Enterprise CRM for AI Integration practice."
)


def require_customer(customer_id: str) -> Customer:
    """Return the customer, or raise a 404 if it doesn't exist."""
    customer = get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return customer


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Report that the service is running."""
    return {"status": "ok"}


@app.get(
    "/tickets/{ticket_id}",
    tags=["tickets"],
    responses={404: {"description": "No ticket with that ID"}},
)
async def read_ticket(ticket_id: str) -> Ticket:
    """Return the Ticket with the given ID.

    Responds 404 if no such ticket exists.
    """
    ticket = get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")
    return ticket


@app.get(
    "/tickets",
    tags=["tickets"],
)
async def search_tickets(status: Status, min_priority: int = 1) -> list[str]:
    """Return list of Ticket ids with a given status, at or above a minimum priority.

    Returns an empty list if no tickets match."""
    return find_tickets(status, min_priority)


@app.get(
    "/customers/{customer_id}",
    tags=["customers"],
    responses={404: {"description": "No Customer with that ID"}},
)
async def read_customer(customer_id: str) -> Customer:
    """Return Customer details by its ID. Responds 404 if no such customer exists."""

    return require_customer(customer_id)


@app.get(
    "/customers/{customer_id}/summary",
    tags=["customers"],
    responses={404: {"description": "No Customer with that ID"}},
)
async def read_customer_summary(customer_id: str) -> CustomerSummary:
    """Return Customer ticket summary details from Customer ID.

    Responds 404 if no such customer exists.
    """
    require_customer(customer_id)
    return summarize_customer(customer_id)


@app.get(
    "/customers/{customer_id}/orders",
    tags=["customers"],
    responses={404: {"description": "No Customer with that ID"}},
)
async def read_customer_orders(customer_id: str) -> list[Order]:
    """Return Customer list of orders from their Customer ID.

    Responds 404 if no such customer exists.
    """
    require_customer(customer_id)
    return orders_by_customer().get(customer_id, [])


@app.get(
    "/customers/{customer_id}/total",
    tags=["customers"],
    responses={404: {"description": "No Customer with that ID"}},
)
async def read_customer_total(customer_id: str) -> CustomerTotal:
    """Return Customer total spent from their ID.

    Responds 404 if no such customer exists.
    """
    require_customer(customer_id)
    return CustomerTotal(
        customer=customer_id,
        total=customer_order_total(customer_id),
    )


@app.post(
    "/tickets",
    tags=["tickets"],
    status_code=201,
    responses={404: {"description": "No Customer with that ID"}},
)
async def open_ticket(new: TicketCreate) -> Ticket:
    """Open a new ticket for an existing customer. Server assigns the ticket ID; New ticket starts as open status with no assignee.

    Responds 404 if no such customer exists.
    """

    require_customer(new.customer)
    return create_ticket(new)


@app.patch(
    "/tickets/{ticket_id}",
    tags=["tickets"],
    responses={
        404: {"description": "No ticket with that ID"},
        422: {"description": "The update breaks a ticket rule"},
    },
)
async def change_ticket(ticket_id: str, changes: TicketUpdate) -> Ticket:
    """Apply a partial update to a ticket's status and/or assignee.

    Responds 404 if the ticket doesn't exist, and 422 if the change breaks
    a ticket rule, such as closing a ticket with no assignee.
    """
    try:
        updated = update_ticket(ticket_id, changes)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=format_errors(e)) from e
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    return updated
