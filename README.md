# mock-crm

A mock enterprise CRM (customers, support tickets, and orders) exposed as a
validated, tested FastAPI service, built as the foundation for an AI
integration portfolio project.

## Why this exists

This project exposes an enterprise system to AI agents, in stages. It currently
provides a typed data layer and an HTTP API over it. An LLM triage pipeline turns
free-text customer messages into prioritized tickets through this API, and a CRM
assistant answers questions and makes changes by calling the API as tools. The
next stage publishes those tools as an MCP server.

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
- CRM assistant with human approval for every write, a read-only mode, and an audit log

## Project structure

```
src/mock_crm/
├── models.py         # Pydantic models: Customer, Ticket, Order, LineItem
├── data.py           # Sample records (stand-in for a database)
├── services.py       # Query functions
├── errors.py         # Validation error formatting
├── api.py            # FastAPI service: HTTP endpoints over the services
└── agent/            # CRM assistant
    ├── tools.py      # Tool inputs, CRM calls, and the tool registry
    ├── loop.py       # Agent loop: approvals, read-only mode, audit log
    └── chat.py       # Command-line chat
tests/                # pytest suite
├── test_models.py    # Pydantic models
├── test_services.py  # Query functions
├── test_api.py       # FastAPI service
└── test_agent.py     # Agent loop and safety rules, with a fake model and a fake CRM
scripts/
├── call_api.py       # Example client calls using httpx
├── triage_inbox.py   # LLM triage pipeline: messages → tickets via the API
├── llm_day4.py       # Triage step used by the pipeline
├── llm_day5.py       # Concurrent triage used by the pipeline
└── eval_tools.py     # Tool-choice eval against the real model
learning/             # Learning exercises: first API calls, prompting, tool use
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

For agent sessions, use `uv run fastapi run src/mock_crm/api.py` instead: `dev`
mode reloads on file changes, which resets the in-memory data.


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


## CRM assistant

`src/mock_crm/agent/` is a command-line assistant for support staff: ask about
tickets and customers in plain English, or ask for changes, and it answers by
calling the CRM's API as tools.

```
You: Does C-1 have any high-priority open tickets?
[round 1] ->search_tickets {'status': 'open', 'min_priority': 4}
[round 2] ->get_ticket {'ticket_id': 'T-3'}
Assistant: Yes. C-1 has one high-priority open ticket: T-3 (priority 5, urgent). It's currently unassigned.
```

How it works:

1. The question and the list of tools (each with a description and an input
   schema generated from a Pydantic model) are sent to Claude.
2. Claude chooses which tools to call and with what arguments.
3. The code validates the arguments, calls the CRM API, and sends the results
   back to Claude.
4. This repeats until Claude answers, with a limit on the number of steps.

**Safety controls**

- **Approval for every write:** a change is shown to the user and runs only if
  they approve it. Reads run without approval.
- **Read-only mode:** write tools are not offered to the model, and are refused
  if requested anyway.
- **Validated arguments:** invalid arguments (such as a customer ID where a
  ticket ID is expected) are rejected before the CRM is called.
- **Safe errors:** CRM errors are returned to the model so it can explain them,
  without internal details.
- **Audit log:** every tool call is recorded, with its arguments and whether it
  was approved.

**Testing**

- **pytest** with a fake model and a fake CRM checks the safety rules and the
  agent loop: no API key, no server, about three seconds.
- **An eval** (`scripts/eval_tools.py`) asks the real model a set of questions
  and measures how often it chooses the right tool.

**Running it**

Requires an Anthropic API key in `.env` and the API running in `run` mode
(`dev` mode reloads on file changes, which resets the data):

```
uv run fastapi run src/mock_crm/api.py
uv run python -m mock_crm.agent.chat
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
- [x] LLM tool calling against the service
- [ ] MCP server wrapping the CRM