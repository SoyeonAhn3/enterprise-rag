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
    patches = [json.loads(call[2]["data"]) for call in updates]
    # The remote service validates hierarchy on PATCH as well as POST.
    # Omitting parent_run_id makes a child update look like a root run.
    assert all(patch["parent_run_id"] == payloads[0]["id"] for patch in patches[:2])
    assert patches[-1]["parent_run_id"] is None
    assert "sensitive-key-must-not-leak" not in json.dumps(payloads)
    assert all(call[2]["timeout"] == (5.0, 5.0) for call in creates)


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


def remote_tree(chunks=None):
    from copy import deepcopy
    from types import SimpleNamespace

    client = TraceClient()
    tracer = LangSmithTracer(configured(), client=client)
    model = FakeClaude()
    model.last_usage = {"input_tokens": 100, "output_tokens": 20,
                        "cache_creation_input_tokens": 30, "cache_read_input_tokens": 40}
    answer = RAGAssistant(FakeRetriever(chunks), model, tracer=tracer).answer("질문")
    runs = {}
    for operation, event in deepcopy(client.events):
        if operation == "create":
            runs[event["id"]] = dict(error=None, end_time=None, outputs=None, child_runs=[], parent_run_id=None)
            runs[event["id"]].update(event)
        else:
            runs[event["run_id"]].update(event)
    run, *children = [SimpleNamespace(**value) for value in runs.values()]
    run.child_runs = children
    client.read_run = lambda *a, **k: run
    client.get_run_url = lambda **k: "https://smith.langchain.com/test-run"
    return tracer, run, answer


def test_trace_readback_checks_actual_context_prompt_answer_and_cached_tokens():
    from eval.check_trace import verify_remote_trace

    tracer, run, answer = remote_tree()
    verified = verify_remote_trace(tracer, answer["trace"], answer)
    assert verified["status"] == "verified_remote"
    assert verified["verified_children"] == ["generation", "retrieval"]
    usage = run.child_runs[1].outputs["usage_metadata"]
    assert usage == {"input_tokens": 170, "output_tokens": 20, "total_tokens": 190,
                     "input_token_details": {"cache_creation": 30, "cache_read": 40}}


@pytest.mark.parametrize("mutation", ["missing_child", "duplicate_child", "wrong_parent", "wrong_type",
                                     "unfinished", "root_answer", "context", "prompt", "tokens", "settings"])
def test_trace_readback_rejects_incomplete_or_mismatched_remote_evidence(mutation):
    from eval.check_trace import verify_remote_trace

    tracer, run, answer = remote_tree()
    retrieval, generation = run.child_runs
    if mutation == "missing_child": run.child_runs.pop()
    elif mutation == "duplicate_child": run.child_runs.append(generation)
    elif mutation == "wrong_parent": generation.parent_run_id = "another-run"
    elif mutation == "wrong_type": generation.run_type = "chain"
    elif mutation == "unfinished": generation.end_time = None
    elif mutation == "root_answer": run.outputs["answer"] = "different answer"
    elif mutation == "context": retrieval.outputs["retrieved_chunks"][0]["text"] += "extra"
    elif mutation == "prompt": generation.inputs["prompt"] += "extra"
    elif mutation == "tokens": generation.outputs["usage_metadata"]["input_tokens"] += 1
    elif mutation == "settings": generation.extra["metadata"]["top_k"] += 1
    with pytest.raises(ValueError):
        verify_remote_trace(tracer, answer["trace"], answer)


def test_empty_context_trace_is_verified_without_generation():
    from eval.check_trace import verify_remote_trace

    tracer, run, answer = remote_tree([])
    assert answer["answerable"] is False
    assert verify_remote_trace(tracer, answer["trace"], answer)["verified_children"] == ["retrieval"]


def test_generation_failure_keeps_usage_without_inventing_an_answer():
    client = TraceClient()
    model = FakeClaude(error=ClaudeError("incomplete response"))
    model.last_usage = {"input_tokens": 100, "output_tokens": 20}
    assistant = RAGAssistant(FakeRetriever(), model, tracer=LangSmithTracer(configured(), client=client))
    with pytest.raises(ClaudeError):
        assistant.answer("질문")
    generation = client.events[-2][1]
    assert generation["error"] == "ClaudeError"
    assert generation["outputs"]["usage_metadata"]["total_tokens"] == 120
    assert "text" not in generation["outputs"]


def test_preflight_never_initializes_network_clients_and_keeps_existing_output(tmp_path, monkeypatch):
    import eval.check_trace as checker

    monkeypatch.setattr(checker, "load_settings", lambda: replace(configured(), anthropic_api_key="hidden"))
    monkeypatch.setattr(checker, "ClaudeClient", lambda *a: pytest.fail("preflight must be offline"))
    monkeypatch.setattr(checker, "LangSmithTracer", lambda *a: pytest.fail("preflight must be offline"))
    path = tmp_path / "readiness.json"
    args = ["--preflight", "--output", str(path), "--retrieval-mode", "pages", "--top-k", "5"]
    assert checker.main(args) == 0
    before = path.read_bytes()
    report = json.loads(before)
    assert report["configuration"]["retrieval_mode"] == "pages"
    assert report["configuration"]["top_k"] == 5
    assert "hidden" not in before.decode() and "sensitive-key" not in before.decode()
    assert checker.main(args) == 1
    assert path.read_bytes() == before


def test_unconfigured_trace_check_does_not_make_billable_calls(monkeypatch, capsys):
    import eval.check_trace as checker

    monkeypatch.setattr(checker, "load_settings", lambda: Settings())
    monkeypatch.setattr(checker, "ClaudeClient", lambda *a: pytest.fail("no API call without tracing setup"))
    assert checker.main([]) == 2
    assert "LANGSMITH_API_KEY" in capsys.readouterr().err
