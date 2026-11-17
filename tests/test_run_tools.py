"""Tests for run_tools, the safety checkpoint. No model and no server needed."""

import asyncio
from types import SimpleNamespace

import httpx
import pytest
import llm_w4d4
from llm_w4d4 import run_tools

# ---------- Setup shared by every test ----------

@pytest.fixture(autouse=True)
def temp_audit_file(tmp_path,monkeypatch):
    """Write audit lines to a temporary file, so tests never touch the real audit.jsonl."""
    monkeypatch.setattr(llm_w4d4,"AUDIT_FILE",tmp_path/"audit.jsonl")

class FakeCRM:
    """Pretends to be the CRM: records every request it receives and always answers 200."""

    def __init__(self):
        self.requests = []

    def handle(self,request):
        self.requests.append(request)
        return httpx.Response(200,json={"id": "T-1", "status": "open", "assignee": "agent-7"})
    
    def client(self):
        return httpx.AsyncClient(base_url="http://crm",transport=httpx.MockTransport(self.handle))

def tool_request(name,args):
     """A fake tool request, shaped like the ones the model sends."""
     return SimpleNamespace(id= "toolu_test", name = name, input = args)

def must_not_ask(summary):
    """An approver that fails the test if anyone asks it for approval."""
    raise AssertionError(f"Approval should not have been requested: {summary}")

# ---------- Tests ----------

def test_read_runs_without_approvals():
    crm = FakeCRM()
    request = tool_request("get_ticket",{"ticket_id":"T-1"})

    results = asyncio.run(run_tools(crm.client(),[request],allow_writes=True,approve=must_not_ask)) # must not ask because its read operation which wont call approve
    assert results[0]["is_error"] is False
    assert [r.method for r in crm.requests] == ["GET"]


def test_declined_write_sends_nothing():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(run_tools(crm.client(), [request], allow_writes=True, approve=lambda s: False))

    assert results[0]["is_error"] is True                   # the model is told it didn't happen
    assert crm.requests == []                               # nothing reached the CRM

def test_approved_write_is_sent():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(run_tools(crm.client(),[request],allow_writes=True,approve=lambda s:True))

    assert results[0]["is_error"] is False
    assert [r.method for r in crm.requests] == ["PATCH"]

def test_read_only_blocks_write():
    crm = FakeCRM()
    request = tool_request("update_ticket", {"ticket_id": "T-1", "assignee": "agent-7"})

    results = asyncio.run(run_tools(crm.client(),[request],allow_writes=False,approve=must_not_ask))

    assert results[0]["is_error"] is True
    assert crm.requests == []

def test_bad_argument_never_reaches_crm():
    crm = FakeCRM()
    request = tool_request("get_ticket",{"ticket_id":"C-1"})

    results = asyncio.run(run_tools(crm.client(),[request],allow_writes=True,approve=must_not_ask))
    assert results[0]["is_error"] is True
    assert crm.requests == []