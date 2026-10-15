"""Exercise offline reproduction against the saved run and damaged copies."""

from copy import deepcopy
import csv
import hashlib
import shutil

import pytest

from config import PROJECT_ROOT
from eval.benchmark import answer_metrics, read, seal, summarize, verify_saved
from eval.check_retrieval import check_evidence
from eval.evaluate import digest, save_json
from eval.render_report import export, write_csv


@pytest.fixture
def run_dir(tmp_path):
    source = PROJECT_ROOT / "eval/results/phase5_v2_20261014"
    for name in ("answers.json", "retrieval_dev.json", "pilot.json", "metrics.json", "review_queue.json"):
        shutil.copyfile(source / name, tmp_path / name)
    return tmp_path


def fingerprints(folder):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}


def test_saved_run_verification_is_read_only_and_needs_no_credentials_or_models(run_dir, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline verification must not initialize settings, models, or API clients.")

    for name in ("load_settings", "create_embeddings", "ClaudeClient"):
        monkeypatch.setattr(f"eval.benchmark.{name}", forbidden)
    before = fingerprints(run_dir)
    result = verify_saved(run_dir)
    assert result["answers"] == result["reviews"] == 120
    assert result["selected_alternative"] == "B" and result["review_queue_entries"] == 34
    assert result["human_review_completed"] is False
    assert fingerprints(run_dir) == before


@pytest.mark.parametrize("damage", [
    "foreign_search", "foreign_pilot", "different_dataset", "wrong_split", "duplicate_answer",
    "unknown_configuration", "changed_grade", "changed_judge_prompt", "changed_evidence",
    "stale_metrics", "stale_queue",
])
def test_export_rejects_inconsistent_artifacts_even_with_valid_individual_hashes(run_dir, damage):
    name = {"foreign_search": "retrieval_dev.json", "foreign_pilot": "pilot.json",
            "stale_metrics": "metrics.json", "stale_queue": "review_queue.json"}.get(damage, "answers.json")
    artifact = read(run_dir / name)
    if damage in {"foreign_search", "foreign_pilot"}:
        artifact["scope"] += " (from another execution)"
    elif damage == "different_dataset":
        artifact["dataset"][0]["question"] += " 변경된 질문"
        artifact["dataset_sha256"] = digest(artifact["dataset"])
    elif damage == "wrong_split":
        artifact["results"][0]["split"] = "final"
    elif damage == "duplicate_answer":
        artifact["results"].append(deepcopy(artifact["results"][0]))
    elif damage == "unknown_configuration":
        artifact["results"][0]["configuration"] = "C"
    elif damage == "changed_grade":
        artifact["reviews"][0]["correct"] = not artifact["reviews"][0]["correct"]
    elif damage == "changed_judge_prompt":
        artifact["reviews"][0]["judge_prompt_sha256"] = "another-rubric"
    elif damage == "changed_evidence":
        check = artifact["results"][0]["evidence_check"]
        check["all_groups_quote_covered"] = not check["all_groups_quote_covered"]
    elif damage == "stale_metrics":
        artifact["splits"]["dev"]["A"]["ai_correctness"] = {"passed": 40, "total": 40, "rate": 1}
    elif damage == "stale_queue":
        artifact["items"].pop()
    save_json(run_dir / name, seal(artifact))
    for filename in ("report.md", "answer_results.csv", "review_queue.csv"):
        (run_dir / filename).write_text("Existing export must survive validation failure.", encoding="utf-8")
    before = fingerprints(run_dir)
    with pytest.raises(ValueError):
        export(run_dir)
    assert fingerprints(run_dir) == before


def test_final_question_cannot_be_used_in_selection_even_when_report_links_match(run_dir):
    search = read(run_dir / "retrieval_dev.json")
    final = next(q for q in search["dataset"] if q["split"] == "final")
    search["comparisons"]["A"]["results"][0].update(id=final["id"], question=final["question"])
    save_json(run_dir / "retrieval_dev.json", seal(search))
    report = read(run_dir / "answers.json")
    report["protocol_sha256"] = search["sha256"]
    save_json(run_dir / "answers.json", seal(report))
    with pytest.raises(ValueError, match="development question"):
        summarize(run_dir)


@pytest.mark.parametrize("outcome", ["failed", "missing"])
def test_no_successful_answers_still_export_with_failures_and_full_denominators(run_dir, outcome):
    report = read(run_dir / "answers.json")
    report["reviews"] = []
    report["execution_events"] = []
    if outcome == "missing":
        report["results"] = []
    else:
        questions = {q["id"]: q for q in report["dataset"]}
        report["results"] = [
            {**{k: r[k] for k in ("id", "question", "split", "configuration")},
             "status": "error", "error_type": "ProviderError", "latency_ms": 5,
             "retrieved_chunks": [], "evidence_check": check_evidence([], questions[r["id"]]["evidence_groups"])}
            for r in report["results"]
        ]
    save_json(run_dir / "answers.json", seal(report))
    metrics = summarize(run_dir)
    export(run_dir)
    for split, expected in (("dev", 40), ("final", 20)):
        for result in metrics["splits"][split].values():
            assert result["ai_correctness"] == {"passed": 0, "total": expected, "rate": 0}
            assert result["latency_ms"]["successful_mean"] is None
            assert result["abstention_contract"]["passed"] == 0
            assert len(result["rag_errors" if outcome == "failed" else "missing"]) == expected
    with (run_dir / "answer_results.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 120
    assert {r["rag_status"] for r in rows} == {"error" if outcome == "failed" else "missing"}
    assert metrics["review_queue"]["flagged_entries"] == 120
    markdown = (run_dir / "report.md").read_text(encoding="utf-8")
    assert "해당 없음 (성공 응답 없음)" in markdown
    assert "답변 누락" in markdown and "채점 실패·미실행·누락" in markdown


@pytest.mark.parametrize("column,value", [("human_notes", "사람이 직접 작성한 검토 메모"), ("human_status", "reviewed")])
def test_regeneration_does_not_overwrite_human_review_work(run_dir, column, value):
    export(run_dir)
    target = run_dir / "review_queue.csv"
    with target.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0][column] = value
    write_csv(target, list(rows[0]), rows)
    before = fingerprints(run_dir)
    with pytest.raises(ValueError, match="human work"):
        export(run_dir)
    assert fingerprints(run_dir) == before


def test_failed_generation_cannot_be_counted_as_correct_by_a_successful_grade():
    question = {"id": "q01", "answerable": True, "category": "single_document", "evidence_groups": []}
    result = {"id": "q01", "status": "error", "retrieved_chunks": [], "latency_ms": 1}
    grade = {"question_id": "q01", "status": "success", "correct": True, "result_sha256": digest(result)}
    metrics = answer_metrics([question], [result], [grade])
    assert metrics["ai_correctness"]["passed"] == 0


@pytest.mark.parametrize("unknown", ["answer", "review"])
def test_metrics_reject_unknown_answers_and_reviews_without_answers(unknown):
    record = {"id": "q99"} if unknown == "answer" else {"question_id": "q99"}
    with pytest.raises(ValueError, match="Unknown results"):
        answer_metrics([], [record] if unknown == "answer" else [], [record] if unknown == "review" else [])
