from copy import deepcopy
import json

import pytest

from eval.check_retrieval import check_evidence
from eval.expanded_cases import build_dataset
from eval.phase6 import (complete_ids, load_report, new_target, retrieval_attempt,
                         save_report, search_metrics, select_candidate, smoke)


def successful(question):
    chunks = []
    for group in question["evidence_groups"]:
        ref = group["any_of"][0]
        chunks.append({"source_id": f"S{len(chunks) + 1}", "source_file": ref["document"],
                       "page": ref["page"], "chunk_id": group["id"], "text": ref["quote"]})
    return {"id": question["id"], "status": "success", "retrieved_chunks": chunks,
            "retrieval_latency_ms": 1, "evidence_check": check_evidence(chunks, question["evidence_groups"])}


def test_search_failure_is_recorded_without_reference_leakage_or_false_success():
    question = build_dataset()[0]

    class Failing:
        def retrieve(self, text):
            assert text == question["question"]
            raise RuntimeError("SECRET_MUST_NOT_BE_SAVED")

    result = retrieval_attempt(Failing(), question)
    assert result["status"] == "error" and result["error_type"] == "RuntimeError"
    assert "SECRET_MUST_NOT_BE_SAVED" not in json.dumps(result)
    metrics = search_metrics([question], [result])
    assert metrics["complete_quote_coverage"] == {"passed": 0, "total": 1, "rate": 0}
    assert metrics["successful"] == 0 and metrics["mean_retrieval_ms"] is None
    assert metrics["failed_or_missing_ids"] == [question["id"]]


def test_missing_retrieval_stays_in_metric_denominator():
    questions = build_dataset()[:2]
    metrics = search_metrics(questions, [successful(questions[0])])
    assert metrics["complete_quote_coverage"]["total"] == 2
    assert metrics["complete_quote_coverage"]["passed"] == 1
    assert metrics["failed_or_missing_ids"] == [questions[1]["id"]]


def test_selection_rejects_lost_complete_evidence_even_with_higher_aggregate():
    questions = build_dataset()[:4]
    comparisons = {}
    for name, covered in (("chunks5", [0, 1]), ("pages5", [1, 2, 3]), ("pages7", [0, 1, 2])):
        results = []
        for index, question in enumerate(questions):
            row = successful(question)
            if index not in covered:
                row["retrieved_chunks"] = []
                row["evidence_check"] = check_evidence([], question["evidence_groups"])
            results.append(row)
        comparisons[name] = {"results": results, "metrics": search_metrics(questions, results)}
    assert select_candidate(comparisons) == "pages7"
    comparisons["pages7"] = deepcopy(comparisons["pages5"])
    assert select_candidate(comparisons) is None
    comparisons["chunks5"]["metrics"]["failed_or_missing_ids"] = ["q01"]
    assert select_candidate(comparisons) is None


def test_report_rejects_content_changes_and_refuses_to_overwrite_attempts(tmp_path):
    target = new_target(tmp_path, "report.json")
    report = {"status": "completed", "results": [{"id": "q01"}]}
    save_report(target, report)
    assert load_report(target)["results"] == report["results"]
    with pytest.raises(ValueError, match="already exists"):
        new_target(tmp_path, "report.json")
    payload = json.loads(target.read_text(encoding="utf-8"))
    payload["results"][0]["id"] = "q02"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="hash"):
        load_report(target)


def test_live_run_rejects_changed_selection_inputs_before_model_access(tmp_path, monkeypatch):
    import eval.phase6 as phase6
    save_report(tmp_path / "retrieval_dev.json", {"status": "completed", "selected_candidate": "pages5",
                                               "source_sha256": {}, "full_dataset_sha256": "old"})

    def forbidden(*args, **kwargs):
        pytest.fail("Must not initialize a model client for stale selection evidence")

    monkeypatch.setattr(phase6, "ClaudeClient", forbidden)
    with pytest.raises(ValueError, match="changed after selection"):
        smoke(tmp_path)
    assert not (tmp_path / "smoke.json").exists()
