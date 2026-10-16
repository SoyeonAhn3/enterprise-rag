from copy import deepcopy
from types import SimpleNamespace

import pytest

from config import Settings
from eval.benchmark import read, seal
from eval.evaluate import save_json
import eval.selection as selection
from tests.test_page_context import hit, pages


def cases():
    question = {"id": "q1", "question": "budget approval account change", "answerable": True,
                "category": "multi_document", "evidence_groups": [
                    {"id": "budget", "any_of": [{"document": "policy.pdf", "page": 1, "quote": "budget"}]},
                    {"id": "bank", "any_of": [{"document": "policy.pdf", "page": 6, "quote": "account change"}]},
                ]}
    absent = {"id": "q2", "question": "unmatched question", "answerable": False,
              "category": "unanswerable", "evidence_groups": []}
    texts = ["budget", "approval", "budget approval", "budget", "approval", "account change"]
    context = pages(dict(enumerate(texts, 1)))
    ranked = [hit(i, text, i) for i, text in enumerate(texts, 1)]
    old = {"ranked_chunks": ranked, "retrieved_chunks": context.assemble(ranked, max_sources=5, max_chars=6000)}
    return context, ranked, [question, absent], old


def test_annotations_only_affect_scoring_not_selected_context():
    context, ranked, questions, old = cases()
    first = selection.compare_candidates(context, questions[0], ranked, old)
    modified = deepcopy(questions[0])
    modified.update(expected_answer="must not reach selection", grading_criteria="must not reach selection",
                    evidence_groups=[{"id": "different", "any_of": [{"document": "policy.pdf", "page": 5, "quote": "approval"}]}])
    second = selection.compare_candidates(context, modified, ranked, old)
    assert first["before"] == second["before"] and first["after"] == second["after"]
    assert first["after_evidence"] != second["after_evidence"]
    assert first["before_evidence"]["all_groups_quote_covered"] is False
    assert first["after_evidence"]["all_groups_quote_covered"] is True


def test_metrics_exclude_unanswerable_evidence_and_do_not_invent_answer_scores():
    context, ranked, questions, old = cases()
    rows = [selection.compare_candidates(context, q, ranked, old) for q in questions]
    summary = selection.summarize(questions, rows)
    assert summary["metrics"]["before"]["complete_required_quotes"]["passed"] == 0
    assert summary["metrics"]["after"]["complete_required_quotes"] == {"passed": 1, "total": 1, "rate": 1}
    assert summary["gains"] == ["q1"] and summary["regressions"] == []
    assert summary["answer_accuracy"] is None and summary["model_calls"] == 0
    with pytest.raises(ValueError):
        selection.summarize(questions, [rows[0], rows[0]])


def test_historical_failures_remain_unknown_without_original_diagnostics():
    original = {"results": [{"configuration": "pages5", "id": "q25", "status": "error",
                             "error_type": "AnswerValidationError", "error_stage": "validation"}]}
    failure = selection.historical_failures(original)[0]
    assert failure["rule"] is None
    assert failure["diagnostic_status"] == "unavailable_in_original_record"


@pytest.fixture
def offline_run(tmp_path, monkeypatch):
    context, ranked, questions, old = cases()
    original = seal({"results": [{"id": q["id"], "configuration": "pages5", "status": "success", **old} for q in questions]})
    signature = {"files": {}}
    protocol = {"dataset": questions, "documents_sha256": {}, "configurations": {"pages5": {"index_signature": signature}}}
    calls = []

    class LocalRetriever:
        index = SimpleNamespace(manifest={"signature": signature})
        page_context = context

        def __init__(self, settings):
            assert settings.retrieval_mode == "pages" and settings.top_k == 5

        def retrieve(self, question):
            calls.append(question)
            return {"ranked_chunks": ranked,
                    "retrieved_chunks": context.assemble(ranked, question=question, max_sources=5, max_chars=6000)}

        def close(self):
            calls.append("closed")

    import llm
    import requests
    monkeypatch.setattr(llm.ClaudeClient, "__init__", lambda *a, **kw: pytest.fail("No model client"))
    monkeypatch.setattr(requests.Session, "request", lambda *a, **kw: pytest.fail("No remote calls"))
    monkeypatch.setattr(selection, "load_completed", lambda path: (protocol, original))
    monkeypatch.setattr(selection, "pdf_fingerprints", lambda path: {})
    monkeypatch.setattr(selection, "run_settings", lambda: Settings())
    monkeypatch.setattr(selection, "PageContext", lambda *a: context)
    monkeypatch.setattr(selection, "Retriever", LocalRetriever)
    output = tmp_path / "selection"
    selection.compare(tmp_path / "source", output)
    return output, calls


def test_comparison_and_readback_use_no_model_and_preserve_existing_output(offline_run):
    output, calls = offline_run
    report = selection.verify_saved(output)
    assert report["status"] == "completed" and report["summary"]["gains"] == ["q1"]
    assert calls == ["budget approval account change", "unmatched question", "closed"]
    with pytest.raises(ValueError, match="new output"):
        selection.compare(output.parent / "source", output)


@pytest.mark.parametrize("change", ["context", "metric", "summary", "failure"])
def test_offline_verify_rejects_resealed_tampering(offline_run, change):
    output, _ = offline_run
    report = read(output / "comparison.json")
    if change == "context": report["rows"][0]["after"][-1]["text"] = "invented"
    elif change == "metric": report["rows"][0]["after_evidence"]["all_groups_quote_covered"] = False
    elif change == "summary": report["summary"]["regressions"] = ["q1"]
    else: report["historical_validation_failures"] = [{"rule": "guessed"}]
    save_json(output / "comparison.json", seal(report))
    with pytest.raises(ValueError, match="reproduce"):
        selection.verify_saved(output)


def test_frozen_source_drift_is_rejected_before_report_reuse(offline_run, monkeypatch):
    output, _ = offline_run
    monkeypatch.setattr(selection, "source_hashes", lambda: {})
    with pytest.raises(ValueError, match="frozen"):
        selection.verify_saved(output)
