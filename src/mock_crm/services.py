"""Query functions over the CRM data, shaped to become LLM tools later."""

from collections import defaultdict
from typing import Annotated

from pydantic import Field

from mock_crm.data import CUSTOMERS, ORDERS, TICKETS
from mock_crm.models import (
    Customer,
    CustomerSummary,
    Order,
    Status,
    Ticket,
    TicketCreate,
    TicketUpdate,
)


def get_customer(customer_id: str) -> Customer | None:
    """Return the customer with the given ID, or None if no such customer exists.

    Use this when the user asks about a specific customer's account details.
    """
    for c in CUSTOMERS:
        if c.id == customer_id:
            return c
    return None


def get_ticket(ticket_id: str) -> Ticket | None:
    """Return the ticket with the given ID, or None if no such ticket exists.

    Use this when the user asks about one specific ticket.
    """
    for t in TICKETS:
        if t.id == ticket_id:
            return t
    return None


def find_tickets(
    status: Status,
    min_priority: Annotated[
        int,
        Field(
            ge=1, le=5, description="Lowest priority to include, 1 (low) to 5 (urgent)"
        ),
    ] = 1,
) -> list[str]:
    """Return IDs of tickets with the given status, at or above a minimum priority.

    Use this when the user asks for tickets in a particular state,
    such as "show me urgent open tickets".
    """
    return [t.id for t in TICKETS if t.status == status and t.priority >= min_priority]


def summarize_customer(customer_id: str) -> CustomerSummary:
    """Summarize a customer's support tickets: total, open, and highest priority.

    Use this when the user asks how many tickets a customer has or how urgent they are.
    Returns zeros for a customer with no tickets.
    """
    customer_tickets = [t for t in TICKETS if t.customer == customer_id]

    return CustomerSummary(
        customer=customer_id,
        ticket_count=len(customer_tickets),
        open_count=sum(1 for t in customer_tickets if t.status == "open"),
        max_priority=max((t.priority for t in customer_tickets), default=0),
    )


def orders_by_customer() -> dict[str, list[Order]]:
    """Group all orders by customer ID."""
    grouped: defaultdict[str, list[Order]] = defaultdict(list)
    for order in ORDERS:
        grouped[order.customer].append(order)
    return dict(grouped)


def customer_order_total(customer_id: str) -> float:
    """Return the combined value of all of a customer's orders, or 0.0 if they have none.

    Use this when the user asks how much a customer has spent.
    """
    return sum(
        (order.total() for order in ORDERS if order.customer == customer_id), 0.0
    )


def next_ticket_id() -> str:
    """Return the next unused ticket id, e.g. T-5 when T-4 is the highest."""

    highest = max((int(t.id.split("-")[1]) for t in TICKETS), default=0)
    return f"T-{highest + 1}"


def create_ticket(new: TicketCreate) -> Ticket:
    """open a new ticket for a customer with status open and no assignee."""
    ticket = Ticket(
        id=next_ticket_id(),
        customer=new.customer,
        status="open",
        priority=new.priority,
    )
    TICKETS.append(ticket)
    return ticket


def update_ticket(ticket_id: str, changes: TicketUpdate) -> Ticket | None:
    """Apply a partial update to a ticket and return the updated ticket.

    Returns None if no ticket has that ID. Raises ValidationError if the
    result breaks a ticket rule, e.g. closing a ticket with no assignee.
    """
    for i, existing in enumerate(TICKETS):
        if existing.id == ticket_id:
            updates = changes.model_dump(exclude_none=True)
            updated = Ticket.model_validate(existing.model_dump() | updates)
            TICKETS[i] = updated
            return updated
    return None
