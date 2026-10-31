# mock-crm

A mock enterprise CRM (customers, support tickets, and orders) exposed as a
validated, tested FastAPI service, built as the foundation for an AI
integration portfolio project.

## Why this exists

This project exposes an enterprise system to AI agents, in stages. It currently
provides a typed data layer and an HTTP API over it. An LLM triage pipeline already
turns free-text customer messages into prioritized tickets through this API. 
Later stages let an LLM call the API through tool use, and publish it as an MCP 
server. Every service function has typed parameters and an LLM-oriented docstring, 
so it can become an agent tool without redesign.

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
├── call_api.py       # example client calls using httpx
├── triage_inbox.py   # LLM triage pipeline: messages → tickets via the API
└── llm_day*.py       # learning exercises: prompting, structured output, async LLM calls
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

## LLM triage pipeline

`scripts/triage_inbox.py` turns free-text customer messages into prioritized
tickets in the CRM:

1. **Health check:** confirms the CRM API is reachable before doing anything,
   so no LLM calls are spent when the CRM is down.
2. **Triage:** each message is sent to Claude, which returns structured output
   validated by Pydantic: queue, priority (1–5), a one-sentence summary, and a
   `needs_human` flag. Calls run concurrently, at most four at a time.
3. **Business rules in code:** priority 4–5 always requires human review,
   regardless of what the model returned.
4. **Ticket creation:** each triaged message becomes a ticket via `POST /tickets`.
   Messages triaged as `other` (not support requests) are ignored.
5. **Report:** counts of tickets created, failures, and ignored messages, a
   breakdown by queue, and the tickets that need human review.

Failures are isolated: a failed LLM call or a rejected API call is logged and
skipped, and the rest of the batch continues.

**Current limitation:** the API stores only customer and priority. Queue,
summary, and `needs_human` appear in the report but are not yet persisted.

Requires an Anthropic API key in a `.env` file (`ANTHROPIC_API_KEY=...`) and
the API running:

```
uv run python scripts/triage_inbox.py
```
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
- [x] LLM triage pipeline: free-text messages become prioritized tickets via the API
- [ ] LLM tool calling against the service
- [ ] MCP server wrapping the CRM