from copy import deepcopy
import json

import pytest

from config import Settings
from eval import quality
from eval.ai_review import review_answer
from eval.benchmark import read, seal
from eval.evaluate import save_json
from eval.expanded_cases import build_dataset
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_benchmark import valid_grade
from tests.test_quality import answer, grade


@pytest.fixture
def custom(tmp_path, monkeypatch):
    # Old known cases are test fixtures; never run the reserved v3 questions.
    cases = deepcopy([build_dataset()[i] for i in (0, 8, 1)])
    for i, q in enumerate(cases):
        q.update(id=f"case_{i}", family=f"family_{i}", test_type="boundary" if q["answerable"] else "unanswerable")
    cases[-1]["split"] = "final"
    path = tmp_path / "questions.json"
    save_json(path, cases)
    monkeypatch.setattr(quality, "run_settings", lambda: Settings(anthropic_api_key="fake-test-key"))
    configurations = {name: {} for name in quality.CONFIGS}
    class Retriever(FakeRetriever):
        top_k = 5
        def __init__(self, name):
            super().__init__()
            self.name = name
        def retrieve(self, question):
            result = super().retrieve(question)
            return {**result, "retrieval_mode": quality.CONFIGS[self.name]["retrieval_mode"],
                    "context_chars": sum(len(c["text"]) for c in result["retrieved_chunks"])}
    retrievers = {name: Retriever(name) for name in quality.CONFIGS}
    monkeypatch.setattr(quality, "open_retrievers", lambda *args: (retrievers, configurations))
    return path, cases, retrievers


def test_freeze_selects_only_requested_questions_and_calculates_limits(custom, tmp_path):
    path, cases, _ = custom
    out = tmp_path / "run"
    protocol = quality.freeze(out, dataset_path=path, split="dev", max_calls=8)
    assert protocol["format_version"] == 2
    assert protocol["dataset"] == cases[:2]
    assert cases[-1]["question"] not in (out / "protocol.json").read_text(encoding="utf-8")
    assert protocol["execution"]["max_answers"] == protocol["execution"]["max_judge_calls"] == 4
    assert protocol["execution"]["max_calls"] == protocol["execution"]["max_total_calls"] == 8
    assert quality.load_protocol(out) == protocol
    quality.check_current_protocol(protocol)
    with pytest.raises(ValueError, match="empty output"):
        quality.freeze(out, dataset_path=path, split="dev")


def test_explicit_final_selection_uses_only_reserved_fixture(custom, tmp_path):
    path, cases, retrievers = custom
    protocol = quality.freeze(tmp_path / "final", dataset_path=path, split="final")
    assert protocol["dataset"] == cases[2:]
    assert protocol["execution"]["max_total_calls"] == 4
    assert all(not r.questions for r in retrievers.values())


@pytest.mark.parametrize("options", [{}, {"split": "all"}, {"split": "dev", "max_calls": 7},
                                     {"split": "dev", "max_calls": -1}, {"split": "dev", "max_calls": True}])
def test_bad_selection_or_budget_fails_before_runtime_initialization(custom, tmp_path, monkeypatch, options):
    monkeypatch.setattr(quality, "run_settings", lambda: pytest.fail("No resources before preflight"))
    with pytest.raises(ValueError):
        quality.freeze(tmp_path / "bad", dataset_path=custom[0], **options)
    assert not (tmp_path / "bad").exists()


@pytest.mark.parametrize("change", ["wording", "rubric", "reference", "unselected_split", "code", "prompt", "documents"])
def test_drift_blocks_live_run_before_clients(custom, tmp_path, monkeypatch, change):
    path, cases, _ = custom
    out = tmp_path / "run"
    quality.freeze(out, dataset_path=path, split="dev")
    if change == "code": monkeypatch.setattr(quality, "source_hashes", lambda: {})
    elif change == "prompt": monkeypatch.setattr(quality, "SYSTEM_PROMPT", "changed")
    elif change == "documents": monkeypatch.setattr(quality, "pdf_fingerprints", lambda *a: {})
    else:
        if change == "wording": cases[0]["question"] += " 다시 설명해주세요."
        elif change == "rubric": cases[0]["grading_criteria"].append("추가 기준")
        elif change == "reference": cases[0]["evidence_groups"][0]["any_of"][0]["quote"] = "없는 규정"
        else: cases[-1]["expected_answer"] += " 최종 평가 기준 수정"
        save_json(path, cases)
    monkeypatch.setattr(quality, "ClaudeClient", lambda *a: pytest.fail("No model after drift"))
    with pytest.raises(ValueError):
        quality.run(out)


@pytest.mark.parametrize("change", ["split", "count", "limit", "attempt_count", "retries", "unsafe_id"])
def test_resealed_invalid_protocol_is_rejected(custom, tmp_path, change):
    out = tmp_path / "run"
    protocol = quality.freeze(out, dataset_path=custom[0], split="dev")
    if change == "split": protocol["dataset_info"]["split"] = "final"
    elif change == "count": protocol["dataset_info"]["question_count"] = 100
    elif change == "limit": protocol["execution"]["max_calls"] = 1
    elif change == "attempt_count": protocol["execution"]["max_answers"] = 120
    elif change == "retries": protocol["execution"]["automatic_retries"] = 1
    else:
        protocol["dataset"][0]["id"] = "../outside"
        protocol["dataset_sha256"] = quality.digest(protocol["dataset"])
    save_json(out / "protocol.json", seal(protocol))
    with pytest.raises(ValueError):
        quality.load_protocol(out)


def test_mock_run_reports_verify_without_source_file_credentials_or_models(custom, tmp_path, monkeypatch):
    path, cases, retrievers = custom
    requests = []
    class Client(FakeClaude):
        def __init__(self, settings):
            super().__init__()
            self.settings = settings
        def generate(self, prompt, **kwargs):
            inputs = json.loads(prompt)
            requests.append(inputs)
            if "criteria" in inputs:
                return json.dumps(valid_grade(inputs))
            assert "expected_answer" not in inputs and "grading_criteria" not in inputs and "references" not in inputs
            if inputs["question"] == cases[1]["question"]:
                return '{"answerable":false,"claims":[]}'
            return self.raw
        def close(self):
            pass
    monkeypatch.setattr(quality, "ClaudeClient", Client)
    out = tmp_path / "run"
    quality.freeze(out, dataset_path=path, split="dev", max_calls=8)
    summary = quality.run(out)
    assert len(requests) == 8
    assert all(r.questions == [q["question"] for q in cases[:2]] for r in retrievers.values())
    assert summary["question_count"] == 2 and summary["dataset_info"]["split"] == "dev"
    assert set(summary["breakdown"]["test_type"]) == {"boundary", "unanswerable"}
    for name in quality.CONFIGS:
        assert summary["assessment"][name]["fully_assessed"] is True
        assert summary["metrics"][name]["ai_correctness"]["total"] == 2
    content = (out / "report.md").read_text(encoding="utf-8")
    assert "2문항" in content and "4개" in content and "120개" not in content and "60문항" not in content
    path.unlink()  # Auditing a frozen historical run must not require its source path.
    monkeypatch.setattr(quality, "ClaudeClient", lambda *a: pytest.fail("Offline audit called model"))
    monkeypatch.setattr(quality, "run_settings", lambda: pytest.fail("Offline audit loaded settings"))
    assert quality.main(["verify", "--output-dir", str(out)]) == 0
    assert quality.summarize(out) == summary
    assert len(requests) == 8
    report = read(out / "answers.json")
    report["reviews"].pop()
    save_json(out / "answers.json", seal(report))
    with pytest.raises(ValueError, match="4 answer/review"):
        quality.load_completed(out)


def test_new_report_distinguishes_judge_error_rag_error_and_missing_answer():
    questions = deepcopy([build_dataset()[i] for i in (0, 1, 8)])
    rows, reviews = [], []
    for name in quality.CONFIGS:
        result = answer(questions[0], name)
        review = grade(questions[0], result)
        review.update(status="error", error_type="TimeoutError")
        rows.append(result)
        reviews.append(review)
        failed = answer(questions[1], name)
        failed.update(status="error", error_stage="validation")
        rows.append(failed)
        client = FakeClaude()
        client.settings = Settings()
        reviews.append({"configuration": name, **review_answer(client, questions[1], failed)})
    summary = quality.analyze_selected(questions, rows, reviews)
    for name in quality.CONFIGS:
        part = summary["assessment"][name]
        assert part["eligible_answers"] == 1 and part["completed_reviews"] == 0
        assert part["judge_errors"] == ["q01"]
        assert part["skipped_failed_answers"] == ["q02"]
        assert part["failure_stages"] == {"validation": 1}
        assert part["end_to_end_ai_correctness"] is None
        assert summary["metrics"][name]["missing"] == ["q09"]
    summary["dataset_info"] = {"split": "dev"}
    content = quality.report_text(summary)
    assert "미완료 — 정확도 미확정" in content
    assert "0/3" in content and "0/1" in content
    empty = quality.analyze_selected(questions, [], [])
    empty["dataset_info"] = {"split": "dev"}
    assert "측정 없음" in quality.report_text(empty)


@pytest.mark.parametrize("args", [
    ["run", "--dataset", "x.json"], ["verify", "--split", "dev"],
    ["report", "--max-calls", "10"], ["freeze", "--against", "x.json"],
    ["validate", "--dataset", "x.json", "--resume"],
])
def test_cli_rejects_ignored_or_misplaced_options(tmp_path, args):
    assert quality.main([*args, "--output-dir", str(tmp_path)]) == 1
