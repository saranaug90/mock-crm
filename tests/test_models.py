"""Tests for the CRM models: valid data passes, invalid data is rejected."""

import pytest
from pydantic import ValidationError

from mock_crm.models import Customer, LineItem, Order, Ticket


def test_ticket_defaults() -> None:
    ticket = Ticket(id="T-1", customer="C-1", status="open")
    assert ticket.priority == 3
    assert ticket.assignee is None


def test_ticket_status_is_normalized() -> None:
    ticket = Ticket.model_validate(
        {"id": "T-1", "customer": "C-1", "status": "  Open "}
    )
    assert ticket.status == "open"


def test_ticket_priority_above_five_is_rejected() -> None:
    with pytest.raises(ValidationError, match="less than or equal to 5"):
        Ticket(id="T-1", customer="C-1", status="open", priority=9)


def test_closed_ticket_without_assignee_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must have an assignee"):
        Ticket(id="T-1", customer="C-1", status="closed")


def test_closed_ticket_with_assignee_is_accepted() -> None:
    ticket = Ticket(id="T-1", customer="C-1", status="closed", assignee="agent-7")
    assert ticket.status == "closed"


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        Ticket.model_validate(
            {"id": "T-1", "customer": "C-1", "status": "open", "sla": "24h"}
        )


def test_customer_email_is_lowercased() -> None:
    customer = Customer(id="C-1", name="Asha", email="Asha@Example.com")
    assert customer.email == "asha@example.com"


def test_order_total() -> None:
    order = Order(
        id="O-1",
        customer="C-1",
        items=[
            LineItem(sku="KB-01", quantity=2, unit_price=49.5),
            LineItem(sku="MS-02", quantity=1, unit_price=25.25),
        ],
    )
    assert order.total() == 124.25


def test_gold_tier_customers_returns_true_for_premium() -> None:
    customer = Customer(
        id="C-1", name="Asha Rao", email="asha@example.com", tier="gold"
    )
    assert customer.is_premium() is True


def test_platinum_tier_customers_returns_true_for_premium() -> None:
    customer = Customer(
        id="C-2", name="Leo Martin", email="leo@example.com", tier="platinum"
    )
    assert customer.is_premium() is True


def test_standard_tier_customers_returns_false_for_premium() -> None:
    customer = Customer(id="C-3", name="Mei Chen", email="mei@example.com")
    assert customer.is_premium() is False


def test_customer_email_without_at_is_rejected() -> None:
    with pytest.raises(ValidationError, match="email must contain @"):
        Customer.model_validate({"id": "C-1", "name": "Leo", "email": "leomail.com"})


def test_order_without_item_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="List should have at least 1 item after validation, not 0",
    ):
        Order.model_validate({"id": "O-1", "customer": "C-1", "items": []})


def test_order_with_duplicate_sku_is_rejected() -> None:
    with pytest.raises(
        ValidationError, match="each SKU may appear only once per order"
    ):
        Order.model_validate(
            {
                "id": "O-1",
                "customer": "C-1",
                "items": [
                    {"sku": "KB-01", "quantity": 2, "unit_price": 49.5},
                    {"sku": "KB-01", "quantity": 2, "unit_price": 49.5},
                ],
            }
        )
