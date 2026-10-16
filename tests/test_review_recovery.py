from copy import deepcopy
import json

import pytest

from config import Settings
from eval.ai_review import review_answer
from eval.benchmark import seal
from eval.evaluate import save_json
from eval.expanded_cases import build_dataset
import eval.recover_reviews as recovery
from llm import ClaudeError
from tests.test_answers import FakeClaude
from tests.test_benchmark import valid_grade
from tests.test_quality import answer, grade, protocol


@pytest.fixture
def source(tmp_path, monkeypatch):
    questions = build_dataset()[:4]
    frozen = protocol(questions)
    frozen["judge"].update(max_tokens=4096, timeout_seconds=60)
    seal(frozen)
    results = [answer(q, "pages5") for q in questions]
    results[-1].update(status="error", error_type="AnswerValidationError")
    reviews = []
    for index, (q, result) in enumerate(zip(questions, results)):
        if index == 2:
            reviews.append(grade(q, result))
        else:
            client = FakeClaude(error=ClaudeError("sanitized failure"))
            client.settings = Settings()
            reviews.append({"configuration": "pages5", **review_answer(client, q, result)})
    original = seal({"status": "completed", "results": results, "reviews": reviews})
    monkeypatch.setattr(recovery, "load_completed", lambda path: (deepcopy(frozen), deepcopy(original)))
    return tmp_path / "original", frozen, original


class FakeJudge:
    def __init__(self, settings, *, fail_at=None):
        self.settings, self.fail_at = settings, fail_at
        self.calls = []
        self.failure = None
        self.closed = False

    def generate(self, prompt, **kwargs):
        inputs = json.loads(prompt)
        self.calls.append(inputs)
        if len(self.calls) == self.fail_at:
            self.failure = {"code": "insufficient_credit", "http_status": 400}
            raise ClaudeError("failure")
        return json.dumps(valid_grade(inputs))

    def close(self):
        self.closed = True


def test_prepare_is_offline_and_only_targets_failed_judges_not_rag_errors_or_completed_grades(source, tmp_path, monkeypatch):
    monkeypatch.setattr(recovery, "load_settings", lambda: pytest.fail("offline preparation must not load keys"))
    monkeypatch.setattr(recovery, "RecoveryClient", lambda *a: pytest.fail("offline preparation must not call providers"))
    output = tmp_path / "recovery"
    plan = recovery.prepare(source[0], output)
    assert plan["targets"] == [("pages5", "q01"), ("pages5", "q02")]
    assert plan["base_answers_sha256"] == source[2]["sha256"]
    assert recovery.load_plan(output)[0]["automatic_retries"] == 0
    with pytest.raises(ValueError, match="empty directory"):
        recovery.prepare(source[0], output)


def test_run_only_grades_saved_answers_and_offline_verification_needs_no_keys(source, tmp_path, monkeypatch):
    import eval.quality as quality

    output = tmp_path / "recovery"
    recovery.prepare(source[0], output)
    judge = FakeJudge(Settings())
    monkeypatch.setattr(recovery, "load_settings", lambda: Settings())
    monkeypatch.setattr(recovery, "RecoveryClient", lambda settings: judge)
    monkeypatch.setattr(quality, "RAGAssistant", lambda *a, **k: pytest.fail("never regenerate RAG answers"))
    state = recovery.run(output)
    assert state["status"] == "completed" and state["remaining"] == []
    assert len(judge.calls) == 2 and judge.closed
    assert judge.calls[0]["answer"] == source[2]["results"][0]["answer"]
    monkeypatch.setattr(recovery, "load_settings", lambda: pytest.fail("verify must be offline"))
    assert recovery.verify_recovery(output)[1] == state
    with pytest.raises(ValueError, match="incomplete"):
        recovery.run(output, resume=True)
    assert len(judge.calls) == 2


def test_provider_failure_stops_immediately_and_explicit_carry_keeps_successes(source, tmp_path, monkeypatch):
    output = tmp_path / "recovery"
    recovery.prepare(source[0], output)
    judge = FakeJudge(Settings(), fail_at=2)
    monkeypatch.setattr(recovery, "load_settings", lambda: Settings())
    monkeypatch.setattr(recovery, "RecoveryClient", lambda settings: judge)
    state = recovery.run(output)
    before = (output / "recovery.json").read_bytes()
    assert state["status"] == "stopped_on_error"
    assert state["successful_recoveries"] == 1
    assert state["remaining"] == [["pages5", "q02"]]
    with pytest.raises(ValueError, match="carry-from"):
        recovery.run(output, resume=True)
    assert len(judge.calls) == 2

    next_output = tmp_path / "next_recovery"
    plan = recovery.prepare(source[0], next_output, carry_from=output)
    assert plan["targets"] == [("pages5", "q02")]
    next_judge = FakeJudge(Settings())
    monkeypatch.setattr(recovery, "RecoveryClient", lambda settings: next_judge)
    assert recovery.run(next_output)["status"] == "completed"
    assert len(next_judge.calls) == 1
    assert (output / "recovery.json").read_bytes() == before


def test_first_provider_failure_does_not_attempt_the_remaining_queue(source, tmp_path, monkeypatch):
    output = tmp_path / "recovery"
    recovery.prepare(source[0], output)
    judge = FakeJudge(Settings(), fail_at=1)
    monkeypatch.setattr(recovery, "load_settings", lambda: Settings())
    monkeypatch.setattr(recovery, "RecoveryClient", lambda settings: judge)
    state = recovery.run(output)
    assert len(judge.calls) == 1 and state["attempted"] == 1
    assert len(state["remaining"]) == 2


def test_recovery_code_drift_stops_before_clients(source, tmp_path, monkeypatch):
    output = tmp_path / "recovery"
    recovery.prepare(source[0], output)
    monkeypatch.setattr(recovery, "code_hashes", lambda: {"changed": "source"})
    monkeypatch.setattr(recovery, "RecoveryClient", lambda *a: pytest.fail("no call after source drift"))
    with pytest.raises(ValueError, match="changed after preparation"):
        recovery.run(output)


def test_pending_attempt_is_never_reissued(source, tmp_path, monkeypatch):
    output = tmp_path / "recovery"
    plan = recovery.prepare(source[0], output)
    save_json(output / "attempts/review_pages5_q01.json", seal({
        "state": "pending", "protocol_sha256": plan["sha256"], "kind": "review",
        "configuration": "pages5", "question_id": "q01"}))
    monkeypatch.setattr(recovery, "RecoveryClient", lambda *a: pytest.fail("no repeated request"))
    with pytest.raises(ValueError, match="Pending"):
        recovery.run(output, resume=True)


def test_credit_failure_category_never_retains_provider_text_or_secret():
    cause = RuntimeError("private provider text")
    cause.status_code = 400
    cause.body = {"error": {"message": "Your credit balance is too low. secret-value"}}
    error = ClaudeError("sanitized failure")
    error.__context__ = cause
    category = recovery.failure_category(error)
    assert category == {"code": "insufficient_credit", "http_status": 400}
    assert "secret-value" not in json.dumps(category)


def test_resealed_recovery_summary_cannot_invent_completed_reviews(source, tmp_path, monkeypatch):
    output = tmp_path / "recovery"
    recovery.prepare(source[0], output)
    monkeypatch.setattr(recovery, "load_settings", lambda: Settings())
    monkeypatch.setattr(recovery, "RecoveryClient", lambda settings: FakeJudge(Settings(), fail_at=1))
    state = recovery.run(output)
    state.update(status="completed", remaining=[])
    save_json(output / "recovery.json", seal(state))
    with pytest.raises(ValueError, match="preserved attempts"):
        recovery.verify_recovery(output)
