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
└── errors.py     # Validation error formatting
tests/            # pytest suite
```

## Running it

Requires [uv](https://docs.astral.sh/uv/).

```
uv sync            # install dependencies
uv run mock-crm    # run the demo
uv run pytest      # run the tests
```

## Roadmap

- [x] Typed, validated data layer
- [ ] Async FastAPI service exposing the CRM
- [ ] LLM tool calling against the service
- [ ] MCP server wrapping the CRM