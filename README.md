# mock-crm

A typed, validated data layer for a mock CRM (customers, support tickets, and
orders), built as the foundation for an AI integration portfolio project.

## Why this exists

This is the first stage of a project that exposes an enterprise system to AI
agents. Later stages wrap this data layer in a FastAPI service, let an LLM call
it through tool use, and publish it as an MCP server. The models and query
functions here are designed for that: every function has typed parameters and
an LLM-oriented docstring, so it can become an agent tool without redesign.

## Features

- Pydantic models with field constraints, normalization, and cross-field rules
  (for example, a closed ticket must have an assignee)
- Strict validation: unknown fields are rejected, not silently dropped
- Query functions shaped as LLM tools: typed inputs, documented behavior
- Readable validation error messages, suitable for feeding back to an LLM
- Fully type-checked (mypy), linted (ruff), and tested (pytest)

## Project structure

```
src/mock_crm/
├── models.py     # Pydantic models: Customer, Ticket, Order, LineItem
├── data.py       # Sample records (stand-in for a database)
├── services.py   # Query functions
├── errors.py     # Validation error formatting
├── api.py        # FastAPI service: HTTP endpoints over the services
tests/            # pytest suite
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

## Roadmap

- [x] Typed, validated data layer
- [x] Async FastAPI service exposing the CRM
- [ ] LLM tool calling against the service
- [ ] MCP server wrapping the CRM