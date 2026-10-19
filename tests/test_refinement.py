from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from config import Settings
from eval.benchmark import seal
from eval.evaluate import digest, save_json
from eval.expanded_cases import build_dataset
from eval.quality import attempt
import eval.refinement as refinement
from tests.test_benchmark import valid_grade
from tests.test_quality import answer
from retrieval_context import PageContext


@pytest.fixture
def local_run(tmp_path, monkeypatch):
    questions = [build_dataset()[i] for i in (0, 8)]
    rows = [answer(q, "pages5") for q in questions]
    for r in rows:
        r["ranked_chunks"] = deepcopy(r["retrieved_chunks"])
    rows[0].update(status="error", error_type="AnswerValidationError", error_stage="validation")
    for key in ("answer", "answerable", "claims", "sources"):
        rows[0].pop(key, None)
    source_data = tmp_path / "questions.json"
    save_json(source_data, questions)
    old_protocol = seal({"format_version": 2, "dataset": questions,
                         "dataset_info": {"path": str(source_data), "split": "dev", "sha256": digest(questions)},
                         "documents_sha256": {}, "configurations": {"pages5": {"index_signature": {}}}})
    old = seal({"results": rows})
    context = PageContext.__new__(PageContext)
    context.pages = {(c["source_file"], c["page"]): c["text"] for c in rows[1]["retrieved_chunks"]}
    calls = {"answers": [], "reviews": [], "closed": 0}

    class LocalRetriever:
        index = SimpleNamespace(manifest={})
        page_context = context

        def __init__(self, settings):
            assert settings.retrieval_mode == "pages" and settings.top_k == 5

        def close(self):
            calls["closed"] += 1

    class LocalClient:
        def __init__(self, settings):
            self.settings = settings

        def generate(self, prompt, **kwargs):
            inputs = json.loads(prompt)
            calls["reviews"].append(inputs)
            assert kwargs["system"] == refinement.JUDGE_SYSTEM
            return json.dumps(valid_grade(inputs))

        def close(self):
            pass

    def new_answer(assistant, question):
        calls["answers"].append(question["id"])
        r = answer(question, "pages5")
        r.pop("configuration")
        return r

    import requests
    monkeypatch.setattr(requests.Session, "request", lambda *a, **kw: pytest.fail("No real network"))
    monkeypatch.setattr(refinement, "load_baseline", lambda p: (deepcopy(old_protocol), deepcopy(old)))
    monkeypatch.setattr(refinement, "run_settings", lambda: Settings(anthropic_api_key="test-placeholder"))
    monkeypatch.setattr(refinement, "Retriever", LocalRetriever)
    monkeypatch.setattr(refinement, "PageContext", lambda *a: context)
    monkeypatch.setattr(refinement, "ClaudeClient", LocalClient)
    monkeypatch.setattr(refinement, "answer_once", new_answer)
    monkeypatch.setattr(refinement, "pdf_fingerprints", lambda p: {})
    monkeypatch.setattr(refinement, "public_configuration", lambda *a: {"index_signature": {}})
    output = tmp_path / "comparison"
    return SimpleNamespace(output=output, source=tmp_path / "baseline", questions=questions, old=old,
                           old_protocol=old_protocol, calls=calls, source_data=source_data)


def freeze(case):
    return refinement.freeze(case.source, case.output, 5)


def test_reuses_failed_and_valid_baseline_answers_and_grades_only_eligible_responses(local_run, monkeypatch):
    case = local_run
    protocol = freeze(case)
    assert protocol["execution"]["max_total_calls"] == 5
    assert case.calls["answers"] == case.calls["reviews"] == []
    summary = refinement.run(case.output)
    assert case.calls["answers"] == [q["id"] for q in case.questions]
    assert len(case.calls["reviews"]) == 3
    assert summary["assessment"]["before"]["fully_assessed"]
    assert summary["assessment"]["before"]["end_to_end_ai_correctness"]["passed"] == 1
    assert summary["assessment"]["after"]["end_to_end_ai_correctness"]["passed"] == 2
    assert summary["paired"]["gains"] == [case.questions[0]["id"]]
    assert summary["review_calls"] == 3 and summary["new_answer_attempts"] == 2
    monkeypatch.setattr(refinement, "ClaudeClient", lambda *a: pytest.fail("Offline verification"))
    assert refinement.summarize(case.output) == summary
    refinement.load_completed(case.output)
    with pytest.raises(ValueError, match="exists"):
        refinement.run(case.output, resume=True)


@pytest.mark.parametrize("change", ["final", "limit", "missing_candidates", "nonempty"])
def test_invalid_plan_stops_before_runtime_or_paid_calls(local_run, monkeypatch, change):
    case = local_run
    if change == "final": case.old_protocol["dataset_info"]["split"] = "final"
    elif change == "missing_candidates": case.old["results"][0].pop("ranked_chunks")
    elif change == "nonempty":
        case.output.mkdir()
        (case.output / "keep.txt").write_text("preserve")
    monkeypatch.setattr(refinement, "Retriever", lambda *a: pytest.fail("No runtime resources"))
    with pytest.raises(ValueError):
        refinement.freeze(case.source, case.output, 4 if change == "limit" else 5)
    assert not case.calls["answers"] and not case.calls["reviews"]


@pytest.mark.parametrize("change", ["code", "dataset", "judge", "pdf", "runtime"])
def test_frozen_drift_blocks_new_model_clients(local_run, monkeypatch, change):
    case = local_run
    freeze(case)
    if change == "code": monkeypatch.setattr(refinement, "source_hashes", lambda: {})
    elif change == "dataset": save_json(case.source_data, [])
    elif change == "judge": monkeypatch.setattr(refinement, "JUDGE_SYSTEM", "different judge")
    elif change == "pdf": monkeypatch.setattr(refinement, "pdf_fingerprints", lambda p: {"changed": "pdf"})
    else: monkeypatch.setattr(refinement, "public_configuration", lambda *a: {"index_signature": {"changed": True}})
    monkeypatch.setattr(refinement, "ClaudeClient", lambda *a: pytest.fail("No paid call"))
    with pytest.raises(ValueError, match="differ"):
        refinement.run(case.output)


@pytest.mark.parametrize("damage", ["judge_settings", "duplicate_dataset_key"])
def test_invalid_frozen_judge_or_ambiguous_dataset_stops_before_paid_requests(local_run, monkeypatch, damage):
    case = local_run
    protocol = freeze(case)
    if damage == "judge_settings":
        protocol["judge"]["model"] = "another-model"
        save_json(case.output / "protocol.json", seal(protocol))
    else:
        text = json.dumps(case.questions)
        identity = json.dumps(case.questions[0]["id"])
        text = text.replace('"id": ' + identity, '"id": ' + identity + ', "id": ' + identity, 1)
        case.source_data.write_text(text, encoding="utf-8")
    monkeypatch.setattr(refinement, "ClaudeClient", lambda *a: pytest.fail("No paid request"))
    with pytest.raises(ValueError):
        refinement.run(case.output)


def test_resume_keeps_completed_answers_and_never_repeats_pending_call(local_run, monkeypatch):
    case = local_run
    protocol = freeze(case)
    q = case.questions[0]
    result = {**answer(q, "pages5"), "configuration": "after"}
    attempt(case.output, protocol, "answer", "after", q["id"], lambda: result, resume=False)
    refinement.run(case.output, resume=True)
    assert case.calls["answers"] == [case.questions[1]["id"]]


def test_pending_attempt_blocks_resume_before_clients(local_run, monkeypatch):
    case = local_run
    protocol = freeze(case)
    def interrupted():
        raise KeyboardInterrupt
    with pytest.raises(KeyboardInterrupt):
        attempt(case.output, protocol, "answer", "after", case.questions[0]["id"], interrupted, resume=False)
    monkeypatch.setattr(refinement, "ClaudeClient", lambda *a: pytest.fail("Never repeat an ambiguous request"))
    with pytest.raises(ValueError, match="incomplete"):
        refinement.run(case.output, resume=True)


@pytest.mark.parametrize("damage", ["missing", "duplicate", "metric", "source", "rank"])
def test_resealed_selection_replay_damage_is_detected(local_run, damage):
    case = local_run
    protocol = freeze(case)
    rows = protocol["selection_replay"]
    if damage == "missing": rows.pop()
    elif damage == "duplicate": rows[1] = deepcopy(rows[0])
    elif damage == "metric": rows[0]["evidence_check"]["all_groups_quote_covered"] = True
    elif damage == "source": rows[0]["sources"][0]["text"] = "not in any source"
    else: rows[0]["sources"][0]["seed_rank"] = 999
    save_json(case.output / "protocol.json", seal(protocol))
    with pytest.raises(ValueError):
        refinement.load_protocol(case.output)


def test_judge_failure_remains_unassessed_and_does_not_become_a_gain(local_run, monkeypatch):
    case = local_run
    freeze(case)
    def failed_review(client, question, result):
        from eval.ai_review import review_answer
        review = review_answer(client, question, result)
        if result["configuration"] == "after":
            review.update(status="error", error_type="TimeoutError", correct=None)
        return review
    monkeypatch.setattr(refinement, "review_answer", failed_review)
    summary = refinement.run(case.output)
    assert summary["assessment"]["after"]["end_to_end_ai_correctness"] is None
    assert summary["paired"]["assessed_outcomes"] == 0
    assert summary["paired"]["gains"] == []
    assert "미확정" in (case.output / "report.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("target", ["answer", "review", "aggregate", "summary", "markdown"])
def test_saved_evidence_and_manual_report_changes_are_not_silently_overwritten(local_run, target):
    case = local_run
    freeze(case)
    refinement.run(case.output)
    if target in ("answer", "review"):
        path = next((case.output / "attempts").glob(f"{target}_after_*.json"))
        value = json.loads(path.read_text(encoding="utf-8"))
        value["payload"]["question" if target == "answer" else "judge_model"] = "changed"
        save_json(path, seal(value))
    elif target in ("aggregate", "summary"):
        path = case.output / ("answers.json" if target == "aggregate" else "summary.json")
        value = json.loads(path.read_text(encoding="utf-8"))
        if target == "aggregate": value["results"].pop()
        else: value["paired"]["gains"] = []
        save_json(path, seal(value))
    else:
        (case.output / "report.md").write_text("manual note", encoding="utf-8")
    with pytest.raises(ValueError):
        refinement.summarize(case.output)
