# mock-crm

A mock enterprise CRM (customers, support tickets, and orders) exposed as a
validated, tested FastAPI service, built as the foundation for an AI
integration portfolio project.

## Why this exists

This project exposes an enterprise system to AI agents, in stages. It currently
provides a typed data layer and an HTTP API over it. Later stages let an LLM
call the API through tool use, and publish it as an MCP server. Every service
function has typed parameters and an LLM-oriented docstring, so it can become
an agent tool without redesign.

## Features

- Pydantic models with field constraints, normalization, and cross-field rules
  (for example, a closed ticket must have an assignee)
- Strict validation: unknown fields are rejected, not silently dropped
- Query functions shaped as LLM tools: typed inputs, documented behavior
- Readable validation error messages, suitable for feeding back to an LLM
- Fully type-checked (mypy), linted (ruff), and tested (pytest)
- REST API with correct status codes (201, 404, 422) and documented error responses
- Business rules re-validated on every update; invalid changes never reach stored data
- End-to-end API tests with isolated test data

## Project structure

```
src/mock_crm/
├── models.py         # Pydantic models: Customer, Ticket, Order, LineItem
├── data.py           # Sample records (stand-in for a database)
├── services.py       # Query functions
├── errors.py         # Validation error formatting
└── api.py            # FastAPI service: HTTP endpoints over the services
tests/                # pytest suite
├── test_api.py       # pytest for FastAPI service
├── test_models.py    # pytest for pydantic models
└── test_services.py  # pytest for Query functions
scripts/
└── call_api.py       # example client calls using httpx
```

## Running it

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync            # install dependencies
uv run mock-crm    # run the demo
uv run pytest      # run the tests
```

## Running the API

```
uv run fastapi dev src/mock_crm/api.py
```

Then open http://127.0.0.1:8000/docs for interactive documentation.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Service health check |
| GET | `/tickets?status=open&min_priority=4` | Search ticket IDs by status and priority |
| GET | `/tickets/{ticket_id}` | Fetch one ticket (404 if missing) |
| POST | `/tickets` | Open a ticket for an existing customer (201) |
| PATCH | `/tickets/{ticket_id}` | Update status and/or assignee; business rules re-validated (422 on violation) |
| GET | `/customers/{customer_id}` | Fetch one customer (404 if missing) |
| GET | `/customers/{customer_id}/summary` | Ticket statistics for a customer |
| GET | `/customers/{customer_id}/orders` | A customer's orders |
| GET | `/customers/{customer_id}/total` | A customer's total spend |

Data is held in memory and resets when the service restarts.

## Design notes

- **Layered design:** `services.py` holds the data logic with no knowledge of
  HTTP; `api.py` translates its results into HTTP status codes. The same
  services can back other interfaces, such as an MCP server, unchanged.
- **Separate input models:** `TicketCreate` and `TicketUpdate` define what a
  caller may send. The server owns the ticket ID and initial status, and
  unknown fields are rejected.
- **Validate before saving:** a PATCH merges the changes onto the current
  ticket and re-validates the whole record before storing it, so an update
  can never produce a ticket that breaks a business rule.
- **Missing vs. empty:** an unknown customer returns 404, while a known
  customer with no orders returns an empty list.


## Roadmap

- [x] Typed, validated data layer
- [x] Async FastAPI service exposing the CRM
- [ ] LLM tool calling against the service
- [ ] MCP server wrapping the CRM