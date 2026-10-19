import json

import pytest

from config import Settings
from grounding import ABSTENTION_MESSAGE, ANSWER_SCHEMA, SYSTEM_PROMPT, AnswerValidationError
from llm import ClaudeError
from rag import RAGAssistant, RetrievalError
from tests.test_grounding import response, sources


class FakeRetriever:
    def __init__(self, chunks=None, error=None):
        self.chunks = sources() if chunks is None else chunks
        self.questions = []
        self.error = error

    def retrieve(self, question):
        self.questions.append(question)
        if self.error:
            raise self.error
        return {"question": question, "retrieved_chunks": self.chunks, "retrieval_latency_ms": 0.0}


class FakeClaude:
    def __init__(self, raw=None, error=None):
        self.raw = json.dumps(response()) if raw is None else raw
        self.error = error
        self.requests = []

    def generate(self, prompt, **kwargs):
        self.requests.append((prompt, kwargs))
        if self.error:
            raise self.error
        return self.raw


def test_one_retrieval_one_generation_preserves_original_results_and_records_latency():
    retriever, client = FakeRetriever(), FakeClaude()
    result = RAGAssistant(retriever, client).answer("  구매와 보안 요건은?  ")
    assert retriever.questions == ["구매와 보안 요건은?"]
    assert len(client.requests) == 1
    prompt, options = client.requests[0]
    assert options == {"system": SYSTEM_PROMPT, "response_schema": ANSWER_SCHEMA}
    assert len(json.loads(prompt)["sources"]) == 3
    assert len(result["sources"]) == 2
    assert result["retrieved_chunks"] == sources()
    assert result["latency_ms"] >= result["generation_latency_ms"] >= 0
    assert result["question"] == "구매와 보안 요건은?"


def test_empty_context_abstains_without_calling_claude():
    retriever, client = FakeRetriever([]), FakeClaude()
    result = RAGAssistant(retriever, client).answer("질문")
    assert result["answer"] == ABSTENTION_MESSAGE
    assert result["answerable"] is False
    assert result["sources"] == result["retrieved_chunks"] == []
    assert result["generation_latency_ms"] == 0
    assert not client.requests


def test_irrelevant_context_abstention_keeps_retrieval_but_no_citations():
    client = FakeClaude('{"answerable":false,"claims":[]}')
    result = RAGAssistant(FakeRetriever(), client).answer("식당 정보는?")
    assert result["answer"] == ABSTENTION_MESSAGE
    assert result["answerable"] is False
    assert not result["sources"]
    assert len(result["retrieved_chunks"]) == 3
    assert len(client.requests) == 1


@pytest.mark.parametrize("question", [None, "", " \n ", "가" * 501])
def test_invalid_question_does_not_retrieve_or_generate(question):
    retriever, client = FakeRetriever(), FakeClaude()
    with pytest.raises(ValueError):
        RAGAssistant(retriever, client).answer(question)
    assert not retriever.questions
    assert not client.requests


@pytest.mark.parametrize("failure", ["retrieval", "provider", "format", "citation"])
def test_failures_are_not_retried_or_converted_to_successful_abstention(failure):
    retriever, client = FakeRetriever(), FakeClaude()
    expected = AnswerValidationError
    if failure == "retrieval":
        retriever.error = RetrievalError("Could not search.")
        expected = RetrievalError
    elif failure == "provider":
        client.error = ClaudeError("Claude request timed out.")
        expected = ClaudeError
    elif failure == "format":
        client.raw = "broken response"
    else:
        payload = response()
        payload["claims"][0]["evidence"][0]["source_id"] = "S99"
        client.raw = json.dumps(payload)
    with pytest.raises(expected):
        RAGAssistant(retriever, client).answer("질문")
    assert len(retriever.questions) == 1
    assert len(client.requests) == (0 if failure == "retrieval" else 1)


def test_provider_diagnostic_survives_saved_answer_without_response_text():
    from eval.benchmark import answer_once

    retriever, client = FakeRetriever(), FakeClaude()
    client.error = ClaudeError("safe message", category="rate_limit", http_status=429)
    result = answer_once(RAGAssistant(retriever, client), {
        "id": "diagnostic", "question": "질문", "evidence_groups": [],
    })
    assert result["status"] == "error"
    assert result["error_stage"] == "generation"
    assert result["provider_error"] == {"category": "rate_limit", "http_status": 429}
    assert result["token_usage"] is None
    assert len(client.requests) == 1


def test_cli_keeps_retrieval_only_as_default_and_closes_clients(monkeypatch, capsys):
    import rag

    retriever, client = FakeRetriever(), FakeClaude()
    closed = []
    retriever.close = lambda: closed.append("retriever")
    client.close = lambda: closed.append("client")
    monkeypatch.setattr(rag, "load_settings", lambda: Settings())
    monkeypatch.setattr(rag, "Retriever", lambda *a, **k: retriever)
    monkeypatch.setattr(rag, "ClaudeClient", lambda *a, **k: client)
    assert rag.main(["질문"]) == 0
    assert "answer" not in json.loads(capsys.readouterr().out)
    assert client.requests == []
    assert closed == ["retriever"]
    closed.clear()
    assert rag.main(["질문", "--answer"]) == 0
    assert json.loads(capsys.readouterr().out)["answerable"] is True
    assert closed == ["client", "retriever"]


def test_cli_failure_does_not_print_a_successful_result(monkeypatch, capsys):
    import rag

    retriever, client = FakeRetriever(), FakeClaude(raw="broken response")
    closed = []
    retriever.close = lambda: closed.append("retriever")
    client.close = lambda: closed.append("client")
    monkeypatch.setattr(rag, "load_settings", lambda: Settings())
    monkeypatch.setattr(rag, "Retriever", lambda *a, **k: retriever)
    monkeypatch.setattr(rag, "ClaudeClient", lambda *a, **k: client)
    assert rag.main(["질문", "--answer"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Answer failed:" in captured.err
    assert "broken response" not in captured.err
    assert closed == ["client", "retriever"]
