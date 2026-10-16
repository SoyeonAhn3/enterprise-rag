import hashlib
import json

import pytest

from eval.benchmark import answer_once
from eval.evaluate import run_evaluation
from grounding import AnswerValidationError, validate_answer
from llm import ClaudeError
from rag import RAGAssistant
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_evaluation import dataset
from tests.test_grounding import response, sources
from tests.test_tracing import TraceClient, configured
from tracing import LangSmithTracer


@pytest.mark.parametrize("raw,rule,path", [
    ("not JSON", "invalid_json", ""),
    ('{"answerable":false,"answerable":true,"claims":[]}', "duplicate_json_key", ""),
    ('{"answerable":NaN,"claims":[]}', "non_json_constant", ""),
    ('{"answerable":false,"claims":[],"secret-extra":1}', "invalid_structure", ""),
    ('{"answerable":"false","claims":[]}', "invalid_field_type", "/answerable"),
    ('{"answerable":true,"claims":null}', "invalid_field_type", "/claims"),
    ('{"answerable":false,"claims":[{}]}', "abstention_with_claims", "/claims"),
    ('{"answerable":true,"claims":[]}', "invalid_claim_count", "/claims"),
    ('{"answerable":true,"claims":[{}]}', "invalid_structure", "/claims/0"),
    (None, "invalid_response_size", ""),
    ("x" * 16001, "invalid_response_size", ""),
])
def test_first_rejected_rule_has_a_stable_safe_location(raw, rule, path):
    with pytest.raises(AnswerValidationError) as caught:
        validate_answer(raw, sources())
    detail = caught.value.diagnostic()
    assert (detail["rule"], detail["path"]) == (rule, path)
    assert "secret-extra" not in json.dumps(detail)


@pytest.mark.parametrize("change,rule,path", [
    ("structure", "invalid_structure", "/claims/1/evidence/0"),
    ("unknown", "unknown_source", "/claims/1/evidence/0/source_id"),
    ("quote", "quote_not_in_source", "/claims/1/evidence/0/quote"),
    ("empty_quote", "missing_quote", "/claims/1/evidence/0/quote"),
    ("empty_evidence", "invalid_citation_count", "/claims/1/evidence"),
    ("text", "invalid_claim_text", "/claims/1/text"),
])
def test_claim_and_citation_positions_identify_the_failed_rule(change, rule, path):
    payload = response()
    claim = payload["claims"][1]
    if change == "structure": claim["evidence"][0]["secret-extra"] = "sensitive-value"
    elif change == "unknown": claim["evidence"][0]["source_id"] = "sensitive-value"
    elif change == "quote": claim["evidence"][0]["quote"] = "sensitive-value"
    elif change == "empty_quote": claim["evidence"][0]["quote"] = " "
    elif change == "empty_evidence": claim["evidence"] = []
    else: claim["text"] = ""
    with pytest.raises(AnswerValidationError) as caught:
        validate_answer(json.dumps(payload), sources())
    detail = caught.value.diagnostic()
    assert (detail["rule"], detail["path"]) == (rule, path)
    assert "sensitive-value" not in json.dumps(detail)


def test_validation_record_keeps_rule_hash_context_usage_without_raw_response_or_retry():
    raw = "sensitive-rejected-text"
    client, retriever = FakeClaude(raw), FakeRetriever()
    client.last_usage = {"input_tokens": 10, "output_tokens": 4}
    record = {"old_failure": "must be cleared"}
    with pytest.raises(AnswerValidationError):
        RAGAssistant(retriever, client).answer("Question", record=record)
    assert record["validation_error"]["rule"] == "invalid_json"
    assert record["response_metadata"] == {"chars": len(raw), "sha256": hashlib.sha256(raw.encode()).hexdigest()}
    assert record["token_usage"] == client.last_usage
    assert record["retrieved_chunks"] == sources()
    assert "sensitive-rejected-text" not in json.dumps(record)
    assert "old_failure" not in record and "answerable" not in record
    assert len(retriever.questions) == len(client.requests) == 1


def test_prompt_failure_has_location_without_a_generated_response():
    chunks = sources()
    chunks[1]["source_id"] = "invalid-source"
    client, record = FakeClaude(), {}
    with pytest.raises(AnswerValidationError):
        RAGAssistant(FakeRetriever(chunks), client).answer("Question", record=record)
    assert record["stage"] == "prompt"
    assert record["validation_error"]["path"] == "/retrieved_chunks/1"
    assert "response_metadata" not in record and not client.requests


def test_provider_errors_do_not_acquire_an_invented_validation_rule():
    result = answer_once(RAGAssistant(FakeRetriever(), FakeClaude(error=ClaudeError("secret"))), dataset()[0])
    assert result["error_stage"] == "generation"
    assert "validation_error" not in result
    assert "secret" not in json.dumps(result)


@pytest.mark.parametrize("runner", ["paired", "baseline"])
def test_both_evaluation_runners_persist_diagnostics_in_error_results(runner, tmp_path):
    assistant = RAGAssistant(FakeRetriever(), FakeClaude("secret-invalid-json"))
    if runner == "paired":
        result = answer_once(assistant, dataset()[0])
    else:
        report = run_evaluation(assistant, dataset(), {}, output=tmp_path / "run.json")
        result = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))["results"][0]
        assert report["status"] == "completed_with_errors"
    assert result["status"] == "error" and result["validation_error"]["rule"] == "invalid_json"
    assert len(result["response_metadata"]["sha256"]) == 64
    assert "secret-invalid-json" not in json.dumps(result)


def test_root_trace_records_rule_without_arbitrary_exception_text():
    client = TraceClient()
    tracer = LangSmithTracer(configured(), client=client)
    with pytest.raises(AnswerValidationError):
        RAGAssistant(FakeRetriever(), FakeClaude("invalid JSON"), tracer=tracer).answer("Question")
    root_update = client.events[-1][1]
    assert root_update["error"] == "AnswerValidationError"
    assert root_update["outputs"]["validation_error"]["rule"] == "invalid_json"
    assert "invalid JSON" not in json.dumps(root_update, default=str)


def test_unclassified_errors_never_leak_exception_text_into_diagnostics():
    detail = AnswerValidationError("secret", rule="secret", path="/secret").diagnostic()
    assert detail["rule"] == "unspecified" and detail["path"] == ""
    assert "secret" not in json.dumps(detail)
