from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from config import Settings
from eval.benchmark import seal
from eval.evaluate import save_json
from eval.expanded_cases import build_dataset
from tests.test_quality import answer
from tests.test_split_judge import decision
import eval.review_split as runner


@pytest.fixture
def case(tmp_path, monkeypatch):
    questions = build_dataset()[:2]
    rows = [answer(q, "pages5") for q in questions]
    old = seal({"dataset": questions, "dataset_info": {"split": "dev"}})
    saved = seal({"results": rows})
    calls = []

    class Client:
        def __init__(self, settings): self.settings = settings
        def close(self): pass
        def generate(self, prompt, **kwargs):
            payload = json.loads(prompt)
            calls.append((payload, kwargs))
            self.last_usage = {"input_tokens": 3, "output_tokens": 2}
            return json.dumps(decision(payload))

    monkeypatch.setattr(runner, "load_source", lambda p: (deepcopy(old), deepcopy(saved)))
    monkeypatch.setattr(runner, "run_settings", lambda: Settings(anthropic_api_key="test-placeholder"))
    monkeypatch.setattr(runner, "ClaudeClient", Client)
    return SimpleNamespace(output=tmp_path / "review", source=tmp_path / "source", old=old, saved=saved, calls=calls, client=Client)


def freeze(case, limit=4):
    return runner.freeze(case.source, case.output, ["pages5"], None, limit)


def test_two_independent_requests_saved_verified_offline_and_never_overwrite_baseline(case, monkeypatch):
    original = deepcopy(case.saved)
    freeze(case)
    summary = runner.run(case.output)
    assert len(case.calls) == 4
    assert ["retrieved" in p for p, _ in case.calls] == [True, False, True, False]
    assert all("references" not in p and "expected_answer" not in p for p, _ in case.calls if "retrieved" in p)
    assert summary["model_calls"] == 4 and summary["complete"]
    assert case.saved == original
    monkeypatch.setattr(runner, "ClaudeClient", lambda *a: pytest.fail("Offline audit"))
    runner.load_completed(case.output)
    assert runner.summarize(case.output) == summary
    with pytest.raises(ValueError, match="already exists"): runner.run(case.output, resume=True)


@pytest.mark.parametrize("damage", ["budget", "unknown_id", "duplicate_id", "unknown_config", "duplicate_config"])
def test_invalid_selection_or_limit_has_no_requests(case, damage):
    configs, ids, limit = ["pages5"], None, 4
    if damage == "budget": limit = 3
    elif damage == "unknown_id": ids = ["absent"]
    elif damage == "duplicate_id": ids = ["q01", "q01"]
    elif damage == "unknown_config": configs = ["absent"]
    else: configs *= 2
    with pytest.raises(ValueError): runner.freeze(case.source, case.output, configs, ids, limit)
    assert not case.calls and not case.output.exists()


@pytest.mark.parametrize("damage", ["source", "model", "prompt", "saved_answer"])
def test_frozen_changes_stop_before_clients(case, monkeypatch, damage):
    freeze(case)
    if damage == "source": monkeypatch.setattr(runner, "source_hashes", lambda: {})
    elif damage == "model": monkeypatch.setattr(runner, "run_settings", lambda: Settings(chat_model="changed"))
    elif damage == "prompt": monkeypatch.setattr(runner, "PROMPTS", {})
    else: case.saved["sha256"] = "changed"
    monkeypatch.setattr(runner, "ClaudeClient", lambda *a: pytest.fail("No client before guard"))
    with pytest.raises(ValueError): runner.run(case.output)


def test_interrupted_stage_is_not_retried_but_completed_stage_can_be_reused(case, monkeypatch):
    protocol = freeze(case)
    original_attempt = runner.attempt

    def interrupted(output, protocol, stage, name, qid, operation, *, resume):
        if stage == "correctness": raise KeyboardInterrupt
        return original_attempt(output, protocol, stage, name, qid, operation, resume=resume)

    monkeypatch.setattr(runner, "attempt", interrupted)
    with pytest.raises(KeyboardInterrupt): runner.run(case.output)
    assert len(case.calls) == 1
    monkeypatch.setattr(runner, "attempt", original_attempt)
    summary = runner.run(case.output, resume=True)
    assert len(case.calls) == 4 and summary["model_calls"] == 4


def test_pending_attempt_blocks_before_model_instantiation(case, monkeypatch):
    protocol = freeze(case)
    target = case.output / "attempts" / "grounding_pages5_q01.json"
    save_json(target, seal({"state": "pending", "protocol_sha256": protocol["sha256"]}))
    monkeypatch.setattr(runner, "ClaudeClient", lambda *a: pytest.fail("Pending call must not repeat"))
    with pytest.raises(ValueError, match="Pending"): runner.run(case.output, resume=True)


def test_failed_request_is_preserved_unassessed_and_stops_further_spending(case, monkeypatch):
    freeze(case)
    def fail(self, prompt, **kwargs):
        case.calls.append("failed")
        raise RuntimeError("DO-NOT-RECORD-SECRET")
    monkeypatch.setattr(case.client, "generate", fail)
    with pytest.raises(ValueError, match="stopped"): runner.run(case.output)
    summary = runner.summarize(case.output)
    assert summary["model_calls"] == summary["review_errors"] == 1
    assert summary["unassessed_answers"] == 2 and not summary["complete"]
    assert all(r["overall_pass"] is None for r in summary["rows"])
    assert "DO-NOT-RECORD-SECRET" not in (case.output / "attempts/grounding_pages5_q01.json").read_text()
    with pytest.raises(ValueError, match="prior failed"): runner.run(case.output, resume=True)
    assert len(case.calls) == 1


@pytest.mark.parametrize("damage", ["input", "raw", "decision", "identity", "unknown_file"])
def test_resealed_stage_tampering_is_detected(case, damage):
    freeze(case); runner.run(case.output)
    path = case.output / "attempts/grounding_pages5_q01.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    payload = obj["payload"]
    if damage == "input": payload["input"]["references"] = [{"source_id": "R1", "text": "not retrieved"}]
    elif damage == "raw": payload["raw_response"] = '{}'
    elif damage == "decision": payload["decision"]["claim_results"][0]["supported"] = False
    elif damage == "identity": payload["result_sha256"] = "changed"
    else: path = case.output / "attempts/unknown.json"
    save_json(path, seal(obj))
    with pytest.raises(ValueError): runner.load_completed(case.output)


def test_invalid_saved_answer_skips_both_model_requests(case):
    case.saved["results"][0]["status"] = "error"
    freeze(case, limit=2)
    summary = runner.run(case.output)
    assert len(case.calls) == 2 and summary["model_calls"] == 2
    assert summary["rows"][0]["answer_status"] == "error"
    assert summary["rows"][0]["overall_pass"] is None


def test_manual_report_is_preserved(case):
    freeze(case); runner.run(case.output)
    (case.output / "report.md").write_text("reviewer's notes", encoding="utf-8")
    with pytest.raises(ValueError, match="manual edits"): runner.summarize(case.output)
    assert (case.output / "report.md").read_text() == "reviewer's notes"


@pytest.mark.parametrize("damage", ["final", "mixed", "implicit"])
def test_source_loader_requires_explicit_dev_only(tmp_path, monkeypatch, damage):
    import eval.refinement as baseline
    questions = build_dataset()[:2]
    old = {"dataset": questions, "dataset_info": {"split": "dev"}}
    if damage == "final": old["dataset_info"]["split"] = "final"
    elif damage == "mixed": questions[0]["split"] = "final"
    else: old.pop("dataset_info")
    save_json(tmp_path / "protocol.json", {"kind": "dev_refinement"})
    monkeypatch.setattr(baseline, "load_completed", lambda p: (old, {}))
    with pytest.raises(ValueError, match="dev baseline"): runner.load_source(tmp_path)


@pytest.mark.parametrize("options", [
    ["freeze", "--max-calls", "4"],
    ["verify", "--configuration", "after"],
    ["report", "--resume"],
])
def test_cli_rejects_ignored_or_incomplete_options(tmp_path, options):
    assert runner.main([*options, "--output-dir", str(tmp_path / "output")]) == 1
    assert not (tmp_path / "output").exists()
