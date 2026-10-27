"""HTTP-level tests for the mock CRM API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from mock_crm.api import app
from mock_crm.data import TICKETS
from mock_crm.models import Ticket

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_tickets() -> Iterator[None]:
    """Restore the ticket list after each test, so tests can't affect each other."""
    original = list(TICKETS)
    yield
    TICKETS[:] = original


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_read_missing_ticket_returns_404() -> None:
    response = client.get("/tickets/T-99")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket T-99 not found"


def test_search_with_invalid_status_returns_422() -> None:
    response = client.get("/tickets", params={"status": "urgent"})
    assert response.status_code == 422


def test_open_ticket_returns_201_with_server_assigned_id() -> None:
    response = client.post("/tickets", json={"customer": "C-2", "priority": 4})
    assert response.status_code == 201
    body = response.json()
    assert body["id"] == "T-5"
    assert body["status"] == "open"


def test_patch_changes_status() -> None:
    response = client.patch("/tickets/T-1", json={"status": "pending"})
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


def test_read_ticket_returns_200() -> None:
    response = client.get("/tickets/T-3")
    assert response.status_code == 200
    ticket = Ticket.model_validate(response.json())
    assert ticket.id == "T-3"
    assert ticket.priority == 5


def test_search_tickets_with_status_and_priority() -> None:
    response = client.get("/tickets", params={"status": "open", "min_priority": 4})
    assert response.status_code == 200
    assert response.json()[0] == "T-3"


def test_open_ticket_with_non_existant_customer_returns_404() -> None:
    response = client.post("/tickets", json={"customer": "C-99", "priority": "1"})
    assert response.status_code == 404


def test_open_ticket_with_extra_parameter_returns_422() -> None:
    response = client.post(
        "/tickets", json={"customer": "C-99", "priority": "1", "id": "1"}
    )
    assert response.status_code == 422


def test_change_ticket_with_business_rule_break_returns_422_and_ticket_unchanged() -> (
    None
):
    response = client.patch("/tickets/T-1", json={"status": "closed"})
    assert response.status_code == 422
    response = client.get("/tickets/T-1")
    assert response.json()["status"] == "open"


def test_change_ticket_returns_200_and_ticket_changed() -> None:
    response = client.patch(
        "/tickets/T-1", json={"status": "closed", "assignee": "Agent-3"}
    )
    assert response.status_code == 200
    response = client.get("/tickets/T-1")
    assert response.json()["status"] == "closed"


def test_change_ticket_with_non_existant_ticket_returns_404() -> None:
    response = client.patch("/tickets/T-99", json={"status": "pending"})
    assert response.status_code == 404


def test_read_customer_summary_with_non_existant_customer_returns_404() -> None:
    response = client.get("/customers/C-99/summary")
    assert response.status_code == 404


def test_read_customer_orders_with_no_orders_returns_empty_list() -> None:
    response = client.get("/customers/C-3/orders")
    assert response.status_code == 200
    assert response.json() == []

def test_open_ticket_with_invalid_priority_returns_404() -> None:
    response = client.post("/tickets", json={"customer": "C-99", "priority": "1"})
    assert response.status_code == 404
