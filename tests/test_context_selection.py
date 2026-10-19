from copy import deepcopy

import pytest

from grounding import build_prompt
from index_store import IndexErrorBase
from tests.test_page_context import hit, pages


def select(texts, question, *, budget=1000, k=3):
    context = pages(dict(enumerate(texts, 1)))
    ranked = [hit(i, text, i) for i, text in enumerate(texts, 1)]
    return context.assemble(ranked, question=question, max_sources=k, max_chars=budget)


def test_final_slot_recovers_a_different_question_requirement_and_keeps_prefix():
    texts = ["예산코드와 잔여예산", "구매 요청과 결재", "예산 설명", "공급업체 계좌 변경 기록"]
    chosen = select(texts, "구매 예산과 계좌 변경 기록을 알려주세요")
    assert [c["page"] for c in chosen] == [1, 2, 4]
    assert chosen[-1]["seed_rank"] == 4 and chosen[-1]["source_id"] == "S3"
    assert chosen[-1]["selection_reason"] == "additional_query_coverage"
    assert chosen[-1]["replaced_seed_rank"] == 3
    assert chosen[-1]["text"] == texts[-1]


def test_replacement_must_retain_unique_query_features_of_original_final_page():
    texts = ["budget rules", "approval rules", "inspection", "account change records"]
    chosen = select(texts, "budget approval inspection account change records")
    assert [c["page"] for c in chosen] == [1, 2, 3]


@pytest.mark.parametrize("question", ["", "unmatched vocabulary", "budget approval"])
def test_no_gain_or_no_question_preserves_vector_order(question):
    chosen = select(["budget", "approval", "budget approval", "budget approval"], question)
    assert [c["page"] for c in chosen] == [1, 2, 3]


def test_one_source_preserves_first_vector_hit():
    chosen = select(["budget", "account change records"], "account change records", k=1)
    assert [c["page"] for c in chosen] == [1]


def test_candidate_must_fit_and_query_gain_uses_only_the_text_actually_sent():
    context = pages({1: "budget", 2: "approval", 3: "budget", 4: "prefix " + "x" * 100 + " account change"})
    ranked = [hit(1, "budget", 1), hit(2, "approval", 2), hit(3, "budget", 3), hit(4, "prefix", 4)]
    chosen = context.assemble(ranked, question="budget approval account change", max_sources=3, max_chars=30)
    assert [c["page"] for c in chosen] == [1, 2, 3]  # Unsent tail cannot earn coverage.
    ranked[-1]["text"] = "account change"
    chosen = context.assemble(ranked, question="budget approval account change", max_sources=3, max_chars=30)
    assert chosen[-1]["page"] == 4 and chosen[-1]["context_kind"] == "chunk"
    assert chosen[-1]["text"] == "account change"
    assert sum(len(c["text"]) for c in chosen) <= 30


def test_duplicate_hits_and_evaluation_annotations_do_not_change_selection_or_input():
    context = pages({1: "budget", 2: "approval", 3: "budget", 4: "account change"})
    ranked = [hit(i, text, i) for i, text in enumerate(["budget", "approval", "budget", "account change"], 1)]
    expected = context.assemble(ranked, question="budget approval account change", max_sources=3, max_chars=1000)
    ranked.append({**ranked[-1], "chunk_id": "duplicate"})
    for c in ranked:
        c.update(expected_answer="secret-annotation", grading_criteria="secret-annotation")
    before = deepcopy(ranked)
    actual = context.assemble(ranked, question="budget approval account change", max_sources=3, max_chars=1000)
    assert [c["page"] for c in actual] == [c["page"] for c in expected]
    assert len({(c["source_file"], c["page"]) for c in actual}) == len(actual)
    assert "secret-annotation" not in build_prompt("Question", actual)
    assert ranked == before


def test_late_corrupted_candidate_cannot_bypass_integrity_checks():
    context = pages({1: "budget", 2: "approval", 3: "budget", 4: "account change"})
    ranked = [hit(1, "budget", 1), hit(2, "approval", 2), hit(3, "budget", 3), hit(4, "fabricated", 4)]
    with pytest.raises(IndexErrorBase):
        context.assemble(ranked, question="budget account change", max_sources=3, max_chars=1000)


def test_direct_sections_replace_redundant_context_even_when_keywords_already_present():
    texts = ["1. Overview\nbudget quotes purchase", "2. Contract\nbudget quotes purchase",
             "FAQ: budget quotes purchase", "3. Shipping\nbudget quotes purchase",
             "4. Security\nbudget quotes purchase", "5. Budget\nReview before approval.",
             "6. Quotes\nObtain a written quotation."]
    chosen = select(texts, "Explain budget and quotes requirements", k=5)
    assert [c["page"] for c in chosen[:2]] == [1, 2]
    assert {6, 7} <= {c["page"] for c in chosen}
    assert [c["source_id"] for c in chosen] == [f"S{i}" for i in range(1, 6)]
    assert len({c["page"] for c in chosen}) == 5


def test_section_refinement_retains_an_existing_distinct_requested_rule():
    texts = ["budget quotes privacy", "budget quotes privacy", "1. Privacy\nprivacy rule",
             "2. Shipping\nbudget quotes privacy", "3. Budget\nbudget rule", "4. Quotes\nquotes rule"]
    chosen = select(texts, "Explain privacy budget quotes", k=5)
    assert {3, 5, 6} <= {c["page"] for c in chosen}
    assert [c["page"] for c in chosen[:2]] == [1, 2]


def test_last_sentence_focus_does_not_promote_background_sections_over_requested_rule():
    texts = ["privacy budget contract", "privacy budget contract", "privacy budget contract",
             "1. Privacy\nprivacy guidance", "2. Contract\ncontract guidance", "3. Budget\nbudget requirements"]
    chosen = select(texts, "The scenario includes privacy and a contract. Explain budget requirements.", k=5)
    assert 6 in {c["page"] for c in chosen}
    assert [c["page"] for c in chosen[:2]] == [1, 2]


def test_unavailable_section_title_in_unsent_page_cannot_trigger_replacement():
    context = pages({1: "budget", 2: "budget", 3: "budget", 4: "budget", 5: "budget",
                     6: "seed " + "x" * 200 + "\n6. Budget\nA direct rule."})
    ranked = [hit(i, "budget", i) for i in range(1, 6)] + [hit(6, "seed", 6)]
    chosen = context.assemble(ranked, question="Explain budget", max_sources=5, max_chars=40)
    assert [c["page"] for c in chosen] == [1, 2, 3, 4, 5]
    assert sum(len(c["text"]) for c in chosen) <= 40
