from dataclasses import replace
import json

import pytest
import requests

from config import Settings, load_settings
from llm import ClaudeError
from rag import RAGAssistant
from tests.test_answers import FakeClaude, FakeRetriever
from tracing import LangSmithTracer


class TraceClient:
    def __init__(self, fail_at=None):
        self.events = []
        self.fail_at = fail_at

    def create_run(self, **kwargs):
        self.events.append(("create", kwargs))
        if len(self.events) == self.fail_at:
            raise RuntimeError("sensitive-key-must-not-leak")

    def update_run(self, **kwargs):
        self.events.append(("update", kwargs))
        if len(self.events) == self.fail_at:
            raise RuntimeError("sensitive-key-must-not-leak")

    def close(self):
        pass


def configured():
    return Settings(langsmith_tracing=True, langsmith_api_key="sensitive-key-must-not-leak")


def test_trace_tree_has_retrieval_and_generation_and_no_configuration_secrets():
    client = TraceClient()
    tracer = LangSmithTracer(configured(), client=client)
    result = RAGAssistant(FakeRetriever(), FakeClaude(), tracer=tracer).answer("질문")
    creates = [event for operation, event in client.events if operation == "create"]
    assert [event["name"] for event in creates] == ["enterprise_rag", "retrieval", "generation"]
    assert all(event["parent_run_id"] == creates[0]["id"] for event in creates[1:])
    assert creates[1]["run_type"] == "retriever"
    assert creates[2]["run_type"] == "llm"
    assert result["trace"]["run_id"] == str(creates[0]["id"])
    payload = json.dumps(client.events, default=str)
    assert "sensitive-key-must-not-leak" not in payload
    assert "expected_answer" not in payload


@pytest.mark.parametrize("failure", [1, 2, 3, 4, 5, 6])
def test_failure_at_any_trace_write_never_blocks_answer_or_retries(failure):
    client = TraceClient(fail_at=failure)
    tracer = LangSmithTracer(configured(), client=client)
    assistant = RAGAssistant(FakeRetriever(), FakeClaude(), tracer=tracer)
    result = assistant.answer("질문")
    assert result["answerable"] is True
    assert result["trace"]["status"] == "unavailable"
    assert len(client.events) == failure
    assert assistant.answer("다음 질문")["answerable"] is True
    assert len(client.events) == failure


@pytest.mark.parametrize("settings,status", [(Settings(), "disabled"),
                                             (Settings(langsmith_tracing=True), "unconfigured")])
def test_disabled_or_missing_configuration_never_calls_trace_service(settings, status):
    client = TraceClient()
    tracer = LangSmithTracer(settings, client=client)
    result = RAGAssistant(FakeRetriever(), FakeClaude(), tracer=tracer).answer("질문")
    assert result["trace"] == {"status": status, "run_id": None}
    assert not client.events


def test_failed_generation_keeps_retrieval_for_evaluation_and_marks_trace_error():
    client = TraceClient()
    tracer = LangSmithTracer(configured(), client=client)
    assistant = RAGAssistant(FakeRetriever(), FakeClaude(error=ClaudeError("timed out")), tracer=tracer)
    record = {}
    with pytest.raises(ClaudeError):
        assistant.answer("질문", record=record)
    assert len(record["retrieved_chunks"]) == 3
    assert record["stage"] == "generation"
    assert record["latency_ms"] >= 0
    assert client.events[-1][1]["error"] == "ClaudeError"
    assert "answerable" not in record


def test_actual_langsmith_sdk_sends_expected_http_tree(monkeypatch):
    calls = []

    def request(self, method, url, **kwargs):
        calls.append((method, url, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = b'{}'
        response.url = url
        return response

    monkeypatch.setattr(requests.Session, "request", request)
    tracer = LangSmithTracer(configured())
    try:
        result = RAGAssistant(FakeRetriever(), FakeClaude(), tracer=tracer).answer("질문")
        assert result["trace"]["status"] == "enabled"
    finally:
        tracer.close()
    creates = [call for call in calls if call[0].upper() == "POST" and call[1].endswith("/runs")]
    updates = [call for call in calls if call[0].upper() == "PATCH"]
    assert len(creates) == len(updates) == 3
    payloads = [json.loads(call[2]["data"]) for call in creates]
    assert [payload["name"] for payload in payloads] == ["enterprise_rag", "retrieval", "generation"]
    assert "sensitive-key-must-not-leak" not in json.dumps(payloads)
    assert all(call[2]["timeout"] == (1.0, 1.0) for call in creates)


def test_optional_trace_settings_preserve_secret_precedence_and_fail_open(tmp_path, monkeypatch):
    for key in ("LANGSMITH_API_KEY", "LANGSMITH_TRACING", "SESSION_QUESTION_LIMIT"):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / ".env"
    env.write_text("LANGSMITH_API_KEY=file-secret\nLANGSMITH_TRACING=invalid\n", encoding="utf-8")
    settings = load_settings(env_file=env, secrets={"LANGSMITH_API_KEY": "server-secret"})
    assert settings.langsmith_api_key == "server-secret"
    assert settings.langsmith_tracing is False
    assert "server-secret" not in repr(settings)
    monkeypatch.setenv("LANGSMITH_API_KEY", "environment-secret")
    assert load_settings(env_file=env).langsmith_api_key == "environment-secret"


def test_trace_verification_requires_remote_children_and_matching_output():
    from types import SimpleNamespace
    from eval.check_trace import verify_remote_trace

    run = SimpleNamespace(id="remote-id", error=None, end_time="done", outputs={"answer": "actual answer"},
                          child_runs=[SimpleNamespace(name=name, error=None, end_time="done")
                                      for name in ("retrieval", "generation")])
    client = SimpleNamespace(read_run=lambda *a, **k: run,
                             get_run_url=lambda **k: "https://smith.langchain.com/test-run")
    tracer = SimpleNamespace(client=client, project="test")
    reference = {"status": "enabled", "run_id": "remote-id"}
    assert verify_remote_trace(tracer, reference, {"answer": "actual answer"})["status"] == "verified_remote"
    run.child_runs.pop()
    with pytest.raises(ValueError, match="incomplete"):
        verify_remote_trace(tracer, reference, {"answer": "actual answer"})


def test_unconfigured_trace_check_does_not_make_billable_calls(monkeypatch, capsys):
    import eval.check_trace as checker

    monkeypatch.setattr(checker, "load_settings", lambda: Settings())
    monkeypatch.setattr(checker, "ClaudeClient", lambda *a: pytest.fail("no API call without tracing setup"))
    assert checker.main([]) == 2
    assert "LANGSMITH_API_KEY" in capsys.readouterr().err
