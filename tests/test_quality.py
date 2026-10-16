from copy import deepcopy
import json

import pytest

from config import Settings
from eval.ai_review import judge_input, review_answer
from eval.benchmark import answer_once, seal
from eval.evaluate import digest, save_json
from eval.expanded_cases import build_dataset
import eval.quality as quality
from rag import RAGAssistant
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_benchmark import valid_grade


def protocol(questions):
    return seal({"format_version": 1, "dataset": questions, "dataset_sha256": digest(questions),
                 "config_overrides": quality.CONFIGS, "configurations": {name: {} for name in quality.CONFIGS},
                 "judge_prompt_sha256": quality.judge_hash(), "judge": {"model": Settings().chat_model}})


def answer(question, name):
    model = FakeClaude() if question["answerable"] else FakeClaude('{"answerable": false, "claims": []}')
    result = {"configuration": name, "split": question["split"],
              **answer_once(RAGAssistant(FakeRetriever(), model), question)}
    result.update(retrieval_mode=quality.CONFIGS[name]["retrieval_mode"],
                  context_chars=sum(len(c["text"]) for c in result["retrieved_chunks"]))
    return result


def grade(question, result, *, correct=True):
    inputs = judge_input(question, result)
    raw = valid_grade(inputs)
    if not correct:
        raw["criterion_results"][0]["satisfied"] = False
        raw["issues"] = [{"kind": "missing_condition", "answer_span": "", "missing_fact": "필수 조건",
                          "reason": "조건 누락", "evidence": []}]
    client = FakeClaude(json.dumps(raw))
    client.settings = Settings()
    return {"configuration": result["configuration"], **review_answer(client, question, result)}


def test_durable_attempt_is_not_repeated_after_success_or_interruption(tmp_path):
    frozen = protocol(build_dataset()[:1])
    calls = []
    operation = lambda: calls.append("called") or {"answer": "saved"}
    value = quality.attempt(tmp_path, frozen, "answer", "pages5", "q01", operation, resume=False)
    assert quality.attempt(tmp_path, frozen, "answer", "pages5", "q01", operation, resume=True) == value
    assert calls == ["called"]
    with pytest.raises(ValueError, match="explicit"):
        quality.attempt(tmp_path, frozen, "answer", "pages5", "q01", operation, resume=False)

    def interrupted():
        calls.append("interrupted")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        quality.attempt(tmp_path, frozen, "answer", "pages5", "q02", interrupted, resume=False)
    with pytest.raises(ValueError, match="pending"):
        quality.attempt(tmp_path, frozen, "answer", "pages5", "q02", operation, resume=True)
    assert calls == ["called", "interrupted"]


def test_ambiguous_temp_file_blocks_calls_and_loading(tmp_path):
    frozen = protocol(build_dataset()[:1])
    folder = tmp_path / "attempts"
    folder.mkdir()
    (folder / "answer_pages5_q01.json.tmp").write_text("partial", encoding="utf-8")
    with pytest.raises(ValueError, match="ambiguous"):
        quality.attempt(tmp_path, frozen, "answer", "pages5", "q01", lambda: pytest.fail("no repeat"), resume=True)
    with pytest.raises(ValueError, match="temporary"):
        quality.read_attempts(tmp_path, frozen)


@pytest.mark.parametrize("mutation", ["duplicate_answer", "duplicate_grade", "question", "evidence", "answer",
                                     "citation", "mode", "grade_link", "grade_input", "grade_raw", "judge_model"])
def test_offline_audit_rejects_semantic_mismatches_even_if_resealed(mutation):
    q = build_dataset()[0]
    result = answer(q, "pages5")
    review = grade(q, result)
    results, reviews = [result], [review]
    quality.validate_records(protocol([q]), results, reviews)
    if mutation == "duplicate_answer": results.append(deepcopy(result))
    elif mutation == "duplicate_grade": reviews.append(deepcopy(review))
    elif mutation == "question": result["question"] = "another question"
    elif mutation == "evidence": result["evidence_check"]["all_groups_quote_covered"] = True
    elif mutation == "answer": result["answer"] += "unvalidated text"
    elif mutation == "citation": result["sources"][0]["page"] += 1
    elif mutation == "mode": result["retrieval_mode"] = "chunks"
    elif mutation == "grade_link": review["result_sha256"] = "other answer"
    elif mutation == "grade_input": review["input"]["question"] = "another question"
    elif mutation == "grade_raw": review["correct"] = False
    elif mutation == "judge_model": review["judge_model"] = "another model"
    # A newly calculated top-level hash must not hide invalid cross-record links.
    sealed = seal({"results": results, "reviews": reviews})
    with pytest.raises(ValueError):
        quality.validate_records(protocol([q]), sealed["results"], sealed["reviews"])


def test_full_denominators_and_paired_gains_regressions_do_not_hide_missing_answers():
    questions = [build_dataset()[i] for i in (0, 1, 8)]
    results, reviews = [], []
    for name in quality.CONFIGS:
        for index, q in enumerate(questions[:2]):
            result = answer(q, name)
            results.append(result)
            reviews.append(grade(q, result, correct=(name == "pages5") == (index == 0)))
    summary = quality.analyze(questions, results, reviews)
    for name in quality.CONFIGS:
        assert summary["metrics"][name]["ai_correctness"] == {"passed": 1, "total": 3, "rate": 1 / 3}
        assert summary["metrics"][name]["missing"] == ["q09"]
        assert summary["metrics"][name]["abstention_contract"]["total"] == 1
    assert summary["paired"] == {"assessed": 2, "gains": ["q01"], "regressions": ["q02"], "unassessed": ["q09"]}


def test_judge_error_stays_unassessed_and_does_not_count_as_a_paired_gain():
    q = build_dataset()[0]
    results = [answer(q, name) for name in quality.CONFIGS]
    reviews = [grade(q, result) for result in results]
    reviews[0].update(status="error", error_type="TimeoutError")
    summary = quality.analyze([q], results, reviews)
    assert summary["paired"]["gains"] == []
    assert summary["paired"]["unassessed"] == [q["id"]]
    assert summary["metrics"]["chunks5"]["ai_correctness"]["passed"] == 0


def test_frozen_code_drift_is_rejected_before_clients_or_calls(tmp_path, monkeypatch):
    monkeypatch.setattr(quality, "run_settings", lambda: Settings())
    monkeypatch.setattr(quality, "open_retrievers", lambda *a: ({}, {name: {} for name in quality.CONFIGS}))
    quality.freeze(tmp_path)
    monkeypatch.setattr(quality, "source_hashes", lambda: {"rag.py": "changed"})
    monkeypatch.setattr(quality, "ClaudeClient", lambda *a: pytest.fail("no request after source drift"))
    with pytest.raises(ValueError, match="changed after freezing"):
        quality.run(tmp_path)
    with pytest.raises(ValueError, match="empty output"):
        quality.freeze(tmp_path)


def test_completed_artifacts_recompute_offline_and_preserve_manual_report(tmp_path, monkeypatch):
    questions = build_dataset()
    frozen = protocol(questions)
    save_json(tmp_path / "protocol.json", frozen)
    for name in quality.CONFIGS:
        for q in questions:
            result = answer(q, name)
            review = grade(q, result)
            quality.attempt(tmp_path, frozen, "answer", name, q["id"], lambda: result, resume=False)
            quality.attempt(tmp_path, frozen, "review", name, q["id"], lambda: review, resume=False)
    results, reviews = quality.read_attempts(tmp_path, frozen)
    save_json(tmp_path / "answers.json", seal({"status": "completed", "protocol_sha256": frozen["sha256"],
                                              "results": results, "reviews": reviews}))
    monkeypatch.setattr(quality, "ClaudeClient", lambda *a: pytest.fail("offline validation must not call a model"))
    monkeypatch.setattr(quality, "load_settings", lambda: pytest.fail("offline validation must not load credentials"))
    summary = quality.summarize(tmp_path)
    assert summary["metrics"]["pages5"]["ai_correctness"]["total"] == 60
    assert quality.main(["verify", "--output-dir", str(tmp_path)]) == 0
    assert quality.summarize(tmp_path) == summary
    report = tmp_path / "report.md"
    report.write_text("human notes", encoding="utf-8")
    with pytest.raises(ValueError, match="manual edits"):
        quality.summarize(tmp_path)
    assert report.read_text(encoding="utf-8") == "human notes"
    # Even a resealed aggregate must match the durable individual attempts.
    saved = json.loads((tmp_path / "answers.json").read_text(encoding="utf-8"))
    saved["reviews"].pop()
    save_json(tmp_path / "answers.json", seal(saved))
    with pytest.raises(ValueError, match="120 answer/review"):
        quality.load_completed(tmp_path)
