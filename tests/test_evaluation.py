from copy import deepcopy
import json

import pytest

from config import PROJECT_ROOT
from eval.evaluate import calculate_metrics, digest, report_fingerprint, run_evaluation, validate_dataset
from grounding import ABSTENTION_MESSAGE
from llm import ClaudeError


def dataset():
    return json.loads((PROJECT_ROOT / "eval/questions.json").read_text(encoding="utf-8"))


def full_report():
    questions = dataset()
    results = []
    for question in questions:
        chunks = []
        for group in question["evidence_groups"]:
            candidate = group["any_of"][-1]  # OR alternatives, not every page required.
            chunks.append({"source_id": f"S{len(chunks) + 1}", "source_file": candidate["document"],
                           "page": candidate["page"], "text": candidate["quote"]})
        results.append({
            "id": question["id"], "status": "success", "retrieved_chunks": chunks,
            "answerable": question["answerable"], "answer": "임의의 답변" if question["answerable"] else ABSTENTION_MESSAGE,
            "claims": [], "sources": [], "latency_ms": 100.0,
        })
    return {"run_id": "test-run", "dataset": questions, "dataset_sha256": digest(questions),
            "configuration": {}, "results": results}


def test_metrics_use_full_retrieval_fixed_denominators_and_no_keyword_grading():
    report = full_report()
    metrics = calculate_metrics(report)
    assert metrics["retrieval_hit_at_3"] == {"passed": 8, "total": 8, "rate": 1.0}
    assert metrics["multi_document_coverage"]["passed"] == 2
    assert metrics["all_required_quotes_retrieved"]["passed"] == 8
    assert metrics["abstention_contract"]["passed"] == 2
    assert metrics["latency_ms"]["all_ten_success_mean"] == 100
    assert metrics["review"]["correctness"] is None  # No answer was semantically graded.


def test_page_match_does_not_imply_quote_or_all_group_coverage():
    report = full_report()
    report["results"][6]["retrieved_chunks"] = report["results"][6]["retrieved_chunks"][:1]
    report["results"][0]["retrieved_chunks"][0]["text"] = "다른 단락"
    metrics = calculate_metrics(report)
    assert metrics["retrieval_hit_at_3"]["passed"] == 8
    assert metrics["multi_document_coverage"]["passed"] == 1
    assert metrics["all_required_quotes_retrieved"]["passed"] == 6


def test_failures_and_missing_runs_do_not_become_abstentions_or_complete_latency():
    report = full_report()
    report["results"][-1]["status"] = "error"
    report["results"].pop(0)
    metrics = calculate_metrics(report)
    assert metrics["failed_ids"] == ["q10"]
    assert metrics["missing_ids"] == ["q01"]
    assert metrics["retrieval_hit_at_3"] == {"passed": 7, "total": 8, "rate": 0.875}
    assert metrics["abstention_contract"]["passed"] == 1
    assert metrics["latency_ms"]["all_ten_success_mean"] is None
    assert metrics["successful"] == 8


def test_runner_preserves_errors_retrieval_and_checkpoints_and_only_forwards_questions(tmp_path):
    questions = dataset()
    calls = []

    class Assistant:
        def answer(self, question, *, record):
            calls.append(question)
            previous = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
            assert len(previous["results"]) == len(calls) - 1
            chunks = [{"source_id": "S1", "source_file": "a.pdf", "page": 1, "text": "근거"}]
            record.update({"stage": "generation", "retrieved_chunks": chunks})
            if len(calls) == 2:
                raise ClaudeError("sensitive-provider-details")
            return {"question": question, "answer": ABSTENTION_MESSAGE, "answerable": False,
                    "claims": [], "sources": [], "retrieved_chunks": chunks, "latency_ms": 1.0}

    output = tmp_path / "run.json"
    report = run_evaluation(Assistant(), questions, {}, output=output)
    assert calls == [item["question"] for item in questions]
    assert report["status"] == "completed_with_errors"
    assert report["results"][1]["status"] == "error"
    assert len(report["results"][1]["retrieved_chunks"]) == 1
    assert report["results"][1]["error"]["stage"] == "generation"
    assert "sensitive-provider-details" not in output.read_text(encoding="utf-8")
    assert calculate_metrics(report) == report["metrics"]
    with pytest.raises(ValueError, match="already exists"):
        run_evaluation(Assistant(), questions, {}, output=output)
    assert len(calls) == 10


def test_reviews_are_bound_to_exact_answers_and_distinguish_agent_from_human():
    report = full_report()
    review = {"report_sha256": report_fingerprint(report), "reviewer_kind": "agent", "reviewer": "test agent",
              "items": [{"id": item["id"], "correct": False, "grounded": False, "notes": "근거 검토 필요"}
                        for item in report["dataset"]]}
    metrics = calculate_metrics(report, review)
    assert metrics["review"]["reviewer_kind"] == "agent"
    assert metrics["review"]["correctness"]["passed"] == 0
    report["results"][0]["answer"] = "changed"
    with pytest.raises(ValueError, match="different answers"):
        calculate_metrics(report, review)


def test_tampered_dataset_or_stored_report_hash_is_rejected():
    report = full_report()
    report["report_sha256"] = report_fingerprint(report)
    report["results"][0]["answer"] = "changed"
    with pytest.raises(ValueError, match="recorded hash"):
        calculate_metrics(report)
    report = full_report()
    report["dataset"][0]["expected_answer"] = "changed reference"
    with pytest.raises(ValueError, match="annotations"):
        calculate_metrics(report)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "empty_quote", "answerable_without_evidence"])
def test_invalid_benchmark_is_rejected_before_any_api_usage(mutation):
    questions = dataset()
    if mutation == "duplicate":
        questions[-1] = deepcopy(questions[0])
    elif mutation == "missing":
        questions.pop()
    elif mutation == "empty_quote":
        questions[0]["evidence_groups"][0]["any_of"][0]["quote"] = " "
    else:
        questions[0]["evidence_groups"] = []
    with pytest.raises(ValueError):
        validate_dataset(questions)
