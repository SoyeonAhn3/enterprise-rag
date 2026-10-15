from copy import deepcopy
import json
from pathlib import Path

import pytest

from config import Settings
from eval.ai_review import judge_input, validate_review
from eval.benchmark import answer_metrics, evidence_metrics, seal, select_alternative, verify
from eval.evaluate import digest
from eval.expanded_cases import build_dataset, validate_dataset
from grounding import AnswerValidationError, build_prompt, validate_answer
from rag import RAGAssistant
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_grounding import sources


def valid_grade(inputs):
    return {"criterion_results": [{"id": c["id"], "satisfied": True, "reason": "필수 사실 일치"} for c in inputs["criteria"]],
            "grounded": True, "rubric_uncertain": False, "issues": [], "notes": "검색 근거와 기준에 부합한다."}


def test_v2_references_match_actual_pdfs_and_paraphrase_families_do_not_leak():
    data = build_dataset()
    validate_dataset(data)
    assert len(data) == 60
    data[-1]["family"] = data[0]["family"]
    with pytest.raises(ValueError, match="leaks"):
        validate_dataset(data)


def test_fifth_source_reaches_generation_schema_and_is_validated_without_reference_leakage():
    chunks = sources()
    for i in (4, 5):
        chunks.append({**deepcopy(chunks[0]), "source_id": f"S{i}", "chunk_id": str(i)})
    retriever = FakeRetriever(chunks)
    retriever.top_k = 5
    raw = json.dumps({"answerable": True, "claims": [{"text": "검색된 사실", "evidence": [
        {"source_id": "S5", "quote": chunks[-1]["text"]}]}]})
    client = FakeClaude(raw)
    result = RAGAssistant(retriever, client).answer("업무 질문")
    assert result["sources"][0]["source_id"] == "S5"
    prompt, options = client.requests[0]
    assert set(json.loads(prompt)) == {"question", "sources"}
    assert options["response_schema"]["properties"]["claims"]["items"]["properties"]["evidence"]["items"]["properties"]["source_id"]["enum"][-1] == "S5"
    with pytest.raises(AnswerValidationError):
        build_prompt("질문", chunks)  # Default still restricts to three.
    payload = json.loads(raw)
    payload["claims"][0]["evidence"][0]["source_id"] = "S6"
    with pytest.raises(AnswerValidationError):
        validate_answer(json.dumps(payload), chunks, max_sources=5)


@pytest.mark.parametrize("k", [0, 11, True, 3.5])
def test_invalid_top_k_is_rejected_before_retrieval(k):
    with pytest.raises(ValueError):
        Settings(top_k=k)


def test_metrics_use_actual_k_and_failed_missing_answers_stay_in_denominator():
    q = build_dataset()[0]
    ref = q["evidence_groups"][0]["any_of"][0]
    chunks = [{"source_id": f"S{i}", "source_file": "wrong.pdf", "page": 1, "text": "무관"} for i in range(1, 5)]
    chunks.append({"source_id": "S5", "source_file": ref["document"], "page": ref["page"], "text": ref["quote"]})
    result = {"id": q["id"], "status": "error", "retrieved_chunks": chunks, "latency_ms": 20}
    assert evidence_metrics([q], [result])["complete_quote_coverage"]["passed"] == 1
    m = answer_metrics([q, build_dataset()[8]], [result], [])
    assert m["ai_correctness"] == {"passed": 0, "total": 2, "rate": 0}
    assert m["abstention_contract"]["passed"] == 0
    assert m["latency_ms"]["successful_mean"] is None
    assert m["rag_errors"] == ["q01"] and m["missing"] == ["q09"]


def test_review_cannot_grade_a_different_answer():
    q = build_dataset()[0]
    result = {"id": q["id"], "status": "error", "retrieved_chunks": [], "latency_ms": 20}
    review = {"question_id": q["id"], "status": "error", "result_sha256": digest(result)}
    result["latency_ms"] = 21
    with pytest.raises(ValueError, match="different answers"):
        answer_metrics([q], [result], [review])


@pytest.mark.parametrize("mutation", ["missing_criterion", "invented_span", "invented_quote", "failure_without_issue"])
def test_judge_output_requires_every_criterion_and_real_spans_and_evidence(mutation):
    q = build_dataset()[0]
    inputs = judge_input(q, {"answerable": True, "answer": "팀장입니다.", "retrieved_chunks": []})
    grade = valid_grade(inputs)
    if mutation == "missing_criterion": grade["criterion_results"].pop()
    elif mutation == "failure_without_issue": grade["grounded"] = False
    else:
        grade["issues"] = [{"kind": "incorrect_fact", "answer_span": "팀장입니다.", "missing_fact": "", "reason": "확인 필요",
                            "evidence": [{"source": "R1", "quote": inputs["references"][0]["text"]}]}]
        if mutation == "invented_span": grade["issues"][0]["answer_span"] = "답변에 없는 문장"
        else: grade["issues"][0]["evidence"][0]["quote"] = "원문에 없는 인용"
    with pytest.raises(ValueError):
        validate_review(json.dumps(grade), inputs)


def test_selection_is_deterministic_and_artifact_tampering_is_rejected():
    same = {key: {"rate": .5} for key in ("complete_quote_coverage", "evidence_group_recall", "page_hit_at_k")}
    comparisons = {name: {"metrics": same} for name in ("A", "B", "C", "D")}
    assert select_alternative(comparisons) == "C"  # k=3 before k=5; then name.
    artifact = seal({"selected": "C"})
    verify(artifact)
    artifact["selected"] = "B"
    with pytest.raises(ValueError):
        verify(artifact)


def test_checkpoint_retries_only_transient_file_replacement(tmp_path, monkeypatch):
    from eval.evaluate import save_json
    calls = []
    original = Path.replace

    def briefly_locked(source, target):
        calls.append(target)
        if len(calls) < 3:
            raise PermissionError("transient Windows file lock")
        return original(source, target)

    monkeypatch.setattr(Path, "replace", briefly_locked)
    monkeypatch.setattr("eval.evaluate.sleep", lambda _: None)
    target = tmp_path / "checkpoint.json"
    save_json(target, {"already_generated_answer": "preserved"})
    assert len(calls) == 3
    assert json.loads(target.read_text()) == {"already_generated_answer": "preserved"}
