import pytest

from eval.check_retrieval import QUESTION_IDS, check_evidence, run_checks


def chunk(document, page, text, source_id="S1"):
    return {"source_file": document, "page": page, "text": text, "source_id": source_id}


def group(identity, candidates):
    return {"id": identity, "any_of": [{"document": document, "page": page, "quote": quote}
                                       for document, page, quote in candidates]}


def test_page_overlap_does_not_imply_quote_or_multi_document_coverage():
    groups = [group("approval", [("a.pdf", 1, "100만원 이하 팀장")]),
              group("security", [("b.pdf", 2, "검토 필요")])]
    result = check_evidence([chunk("a.pdf", 1, "같은 페이지지만 다른 문단")], groups)
    assert result["page_hit_at_3"] is True
    assert result["all_groups_page_covered"] is False
    assert result["all_groups_quote_covered"] is False
    assert result["groups"][0]["quote_sources"] == []


def test_alternative_evidence_accepts_whitespace_but_preserves_amount_and_negation():
    groups = [group("approval", [("a.pdf", 1, "다른 근거"), ("a.pdf", 3, "100만원 이하 팀장")]),
              group("security", [("b.pdf", 2, "검토 필요")])]
    chunks = [chunk("a.pdf", 3, "100만원\n이하 팀장"), chunk("b.pdf", 2, "검토\n필요", "S2")]
    assert check_evidence(chunks, groups)["all_groups_quote_covered"] is True
    chunks[0]["text"] = "200만원 이하 팀장"
    chunks[1]["text"] = "검토 불필요"
    result = check_evidence(chunks, groups)
    assert result["all_groups_page_covered"] is True
    assert result["all_groups_quote_covered"] is False


def test_empty_evidence_is_not_counted_as_success():
    result = check_evidence([chunk("a.pdf", 1, "something")], [])
    assert not any(result[name] for name in ("page_hit_at_3", "all_groups_page_covered", "all_groups_quote_covered"))


def test_smoke_check_sends_only_questions_to_retriever_and_keeps_all_chunks():
    questions = [{"id": identity, "question": f"question {identity}", "expected_answer": "never forward this",
                  "evidence_groups": [group("fact", [("a.pdf", 1, "known fact")])]} for identity in QUESTION_IDS]

    class Recorder:
        def __init__(self):
            self.inputs = []

        def retrieve(self, question):
            self.inputs.append(question)
            return {"question": question, "retrieved_chunks": [chunk("a.pdf", 1, "known fact", f"S{i}") for i in range(1, 4)]}

    retriever = Recorder()
    results = run_checks(retriever, questions)
    assert retriever.inputs == [item["question"] for item in questions]
    assert len(results) == 3
    assert all(len(result["retrieved_chunks"]) == 3 for result in results)
    with pytest.raises(ValueError, match="dataset"):
        run_checks(retriever, questions[:1])
