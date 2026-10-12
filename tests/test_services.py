"""Tests for the CRM query functions, using the sample data in data.py."""

from mock_crm.services import (
    customer_order_total,
    find_tickets,
    get_customer,
    get_ticket,
    orders_by_customer,
    summarize_customer,
)


def test_get_ticket_found() -> None:
    ticket = get_ticket("T-1")
    assert ticket is not None
    assert ticket.customer == "C-1"


def test_get_ticket_missing_returns_none() -> None:
    assert get_ticket("T-99") is None


def test_find_urgent_open_tickets() -> None:
    assert find_tickets("open", min_priority=4) == ["T-3"]


def test_summarize_customer_with_no_tickets() -> None:
    summary = summarize_customer("C-9")
    assert summary.ticket_count == 0
    assert summary.max_priority == 0


def test_get_customer_found() -> None:
    customer = get_customer("C-2")
    assert customer is not None
    assert customer.name == "Leo Martin"


def test_get_customer_missing_returns_none() -> None:
    assert get_customer("C-99") is None


def test_orders_by_customer_returns_correct_order_list() -> None:
    c1_orders = orders_by_customer()["C-1"]
    assert [o.id for o in c1_orders] == ["O-1", "O-3"]


def test_customer_order_total_returns_order_sum() -> None:
    assert customer_order_total("C-1") == 160.25
    assert customer_order_total("C-9") == 0.0
