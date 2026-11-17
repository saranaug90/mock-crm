"""Tests for the CRM agent: run_tools safety rules and the run_agent loop. No model and no server needed."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
import llm_w4d4
from llm_w4d4 import MAX_ROUNDS, run_tools, run_agent

from anthropic.types import ToolUseBlock, TextBlock


# ---------- Setup shared by every test ----------


@pytest.fixture(autouse=True)
def temp_audit_file(tmp_path, monkeypatch):
    """Write audit lines to a temporary file, so tests never touch the real audit.jsonl."""
    monkeypatch.setattr(llm_w4d4, "AUDIT_FILE", tmp_path / "audit.jsonl")


class FakeCRM:
    """Pretends to be the CRM: records every request it receives and always answers 200."""

    def __init__(self):
        self.requests = []

    def handle(self, request):
        self.requests.append(request)
        return httpx.Response(
            200, json={"id": "T-1", "status": "open", "assignee": "agent-7"}
        )

    def client(self):
        return httpx.AsyncClient(
            base_url="http://crm", transport=httpx.MockTransport(self.handle)
        )


class FakeModel:
    """Pretends to be the model: returns prepared replies in order, and counts the calls."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0  # how many times the agent called the model
        self.tools_offered = []  # tool names the agent offered on the last call

    async def create(self, **kwargs):
        self.calls += 1
        self.tools_offered = [t["name"] for t in kwargs["tools"]]
        if not self.replies:
            raise AssertionError("The agent called the model more times than expected")
        return self.replies.pop(0)


def tool_request(name, args):
    """A fake tool request, shaped like the ones the model sends."""
    return SimpleNamespace(id="toolu_test", name=name, input=args)


def must_not_ask(summary):
    """An approver that fails the test if anyone asks it for approval."""
    raise AssertionError(f"Approval should not have been requested: {summary}")


def model_asks_for(name, args):
    """A model reply that asks for one tool."""
    block = ToolUseBlock.model_construct(
        type="tool_use", id="toolu_1", name=name, input=args
    )
    return SimpleNamespace(stop_reason="tool_use", content=[block])


def model_says(text):
    """A model reply that answers in words."""
    block = TextBlock.model_construct(type="text", text=text)
    return SimpleNamespace(stop_reason="end_turn", content=[block])


# ---------- Tests ----------


def test_read_runs_without_approvals():
    crm = FakeCRM()
    request = tool_request("get_ticket", {"ticket_id": "T-1"})

    results = asyncio.run(
        run_tools(crm.client(), [request], allow_writes=True, approve=must_not_ask)
    )  # must not ask because its read operation which wont call approve
    assert results[0]["is_error"] is False
    assert [r.method for r in crm.requests] == ["GET"]


def test_declined_write_sends_nothing():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(
        run_tools(crm.client(), [request], allow_writes=True, approve=lambda s: False)
    )

    assert results[0]["is_error"] is True  # the model is told it didn't happen
    assert crm.requests == []  # nothing reached the CRM


def test_approved_write_is_sent():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(
        run_tools(crm.client(), [request], allow_writes=True, approve=lambda s: True)
    )

    assert results[0]["is_error"] is False
    assert [r.method for r in crm.requests] == ["PATCH"]


def test_read_only_blocks_write():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(
        run_tools(crm.client(), [request], allow_writes=False, approve=must_not_ask)
    )

    assert results[0]["is_error"] is True
    assert crm.requests == []


def test_bad_argument_never_reaches_crm():
    crm = FakeCRM()
    request = tool_request("get_ticket", {"ticket_id": "C-1"})

    results = asyncio.run(
        run_tools(crm.client(), [request], allow_writes=True, approve=must_not_ask)
    )
    assert results[0]["is_error"] is True
    assert crm.requests == []


def test_agent_answers_without_tools():
    crm = FakeCRM()
    model = FakeModel([model_says("Priority runs from 1 to 5.")])
    llm = SimpleNamespace(messages=model)
    question = [{"role": "user", "content": "what is priority?"}]

    answer = asyncio.run(run_agent(llm, crm.client(), question, approve=must_not_ask))

    assert answer == "Priority runs from 1 to 5."  # the prepared answer came back
    assert model.calls == 1  # the model was asked once
    assert crm.requests == []  # no tool ran, so the CRM got nothing


def test_agent_runs_tool_then_answers():
    crm = FakeCRM()
    model = FakeModel(
        [model_asks_for("get_ticket", {"ticket_id": "T-1"}), model_says("T-1 is open.")]
    )
    llm = SimpleNamespace(messages=model)
    question = [{"role": "user", "content": "Status of T-1?"}]

    answer = asyncio.run(run_agent(llm, crm.client(), question, approve=must_not_ask))

    assert answer == "T-1 is open."  # the final prepared answer came back
    assert model.calls == 2  # asked twice: before and after the tool
    assert [r.method for r in crm.requests] == ["GET"]  # the tool really ran: one GET


def test_read_only_does_not_offer_update():
    crm = FakeCRM()
    model = FakeModel([model_says("I can’t make changes here.")])
    llm = SimpleNamespace(messages=model)
    question = [{"role": "user", "content": "update assignee for T-1 as agent-7"}]

    answer = asyncio.run(
        run_agent(llm, crm.client(), question, allow_writes=False, approve=must_not_ask)
    )

    assert "update_ticket" not in model.tools_offered
    assert answer == "I can’t make changes here."
    assert "get_ticket" in model.tools_offered


def test_agent_stops_at_step_limit():
    crm = FakeCRM()
    model = FakeModel(
        [model_asks_for("get_ticket", {"ticket_id": "T-1"}) for _ in range(MAX_ROUNDS)]
    )

    llm = SimpleNamespace(messages=model)
    question = [{"role": "user", "content": "Status of T-1?"}]

    answer = asyncio.run(run_agent(llm, crm.client(), question, approve=must_not_ask))

    assert (
        answer == "Sorry, that needed too many steps. Please try a narrower question."
    )
    assert model.calls == MAX_ROUNDS


def test_declined_write_then_answer():
    crm = FakeCRM()
    model = FakeModel(
        [
            model_asks_for(
                "update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"}
            ),
            model_says("OK, I left it unchanged."),
        ]
    )
    llm = SimpleNamespace(messages=model)

    question = [{"role": "user", "content": "update assignee for T-1 as agent-7"}]

    answer = asyncio.run(
        run_agent(
            llm, crm.client(), question, allow_writes=True, approve=lambda s: False
        )
    )

    assert answer == "OK, I left it unchanged."
    assert model.calls == 2
    assert crm.requests == []
