import pytest

from eval.check_answers import QUESTION_IDS, run_checks
from grounding import ABSTENTION_MESSAGE
from tests.test_grounding import sources


class Recorder:
    def __init__(self, *, incorrectly_answer=False):
        self.inputs = []
        self.incorrectly_answer = incorrectly_answer

    def answer(self, question):
        self.inputs.append(question)
        answerable = question not in ("question q09", "question q10") or self.incorrectly_answer
        return {
            "question": question, "answer": "검토가 필요합니다. [S2]" if answerable else ABSTENTION_MESSAGE,
            "answerable": answerable, "claims": [{"text": "검토가 필요합니다."}] if answerable else [],
            "sources": [{"source_id": "S2"}] if answerable else [], "retrieved_chunks": sources(),
            "latency_ms": 1.0,
        }


def questions():
    return [{
        "id": identity, "question": f"question {identity}", "answerable": identity not in ("q09", "q10"),
        "expected_answer": "NEVER FORWARD THIS", "grading_criteria": ["NEVER FORWARD THIS"],
        "evidence_groups": [] if identity in ("q09", "q10") else [
            {"id": "security", "any_of": [{"document": "security.pdf", "page": 1, "quote": "사전 검토 필요."}]},
        ],
    } for identity in QUESTION_IDS]


def test_live_checker_forwards_only_questions_and_marks_semantic_review_pending():
    recorder = Recorder()
    results = run_checks(recorder, questions())
    assert recorder.inputs == [item["question"] for item in questions()]
    assert all(result["checks_passed"] for result in results)
    assert all(result["manual_review_required"] for result in results)
    assert all(len(result["retrieved_chunks"]) == 3 for result in results)
    assert "all_required_quotes_retrieved" not in results[-1]["checks"]


def test_answering_an_unanswerable_question_is_a_failed_smoke_check():
    results = run_checks(Recorder(incorrectly_answer=True), questions())
    assert not results[-1]["checks_passed"]
    assert not results[-1]["checks"]["answerability_matches"]
    assert not results[-1]["checks"]["fixed_abstention_without_citations"]


def test_checker_requires_all_selected_questions_before_making_requests():
    recorder = Recorder()
    with pytest.raises(ValueError, match="dataset"):
        run_checks(recorder, questions()[:1])
    assert recorder.inputs == []
