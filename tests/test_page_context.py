from dataclasses import replace
from copy import deepcopy
import json

import pytest

from config import ConfigurationError, DOCUMENTS_DIR, Settings, load_settings, pdf_fingerprints
from grounding import AnswerValidationError, build_prompt, validate_answer
from index_store import IndexErrorBase, index_signature
from rag import RAGAssistant, Retriever
from retrieval_context import PageContext
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_index_and_retrieval import workspace, indexed


def hit(page, text, identity, *, document="policy.pdf"):
    return {"source_id": f"S{identity}", "source_file": document, "page": page,
            "chunk_id": str(identity), "text": text, "distance": identity / 100}


def pages(mapping):
    context = PageContext.__new__(PageContext)
    context.pages = {("policy.pdf", page): text for page, text in mapping.items()}
    return context


def test_distinct_pages_restore_split_clause_and_keep_raw_hits_unchanged():
    context = pages({1: "Delivery starts the clock.\nRegister within three days.",
                     2: "IT assigns an asset number within five days after acceptance."})
    ranked = [hit(1, "Delivery starts the clock.", 1),
              hit(1, "Register within three days.", 2), hit(2, "IT assigns an asset number", 3)]
    original = deepcopy(ranked)
    selected = context.assemble(ranked, max_sources=2, max_chars=500)
    assert [c["page"] for c in selected] == [1, 2]
    assert [c["source_id"] for c in selected] == ["S1", "S2"]
    assert [c["seed_rank"] for c in selected] == [1, 3]
    assert selected[0]["text"] == context.pages[("policy.pdf", 1)]
    assert selected[0]["context_kind"] == "page"
    assert selected[0]["chunk_id"].startswith("page:")
    assert ranked == original


@pytest.mark.parametrize("budget,expected", [(45, ["A" * 40, "B" * 5]), (30, ["A" * 20, "B" * 5]),
                                            (15, ["B" * 5]), (4, [])])
def test_budget_uses_whole_page_or_seed_or_skips_without_clipping(budget, expected):
    context = pages({1: "A" * 40, 2: "B" * 5})
    selected = context.assemble([hit(1, "A" * 20, 1), hit(2, "B" * 5, 2)], max_sources=2, max_chars=budget)
    assert [c["text"] for c in selected] == expected
    assert sum(len(c["text"]) for c in selected) <= budget
    assert [c["source_id"] for c in selected] == [f"S{i + 1}" for i in range(len(selected))]
    if selected and selected[0]["text"] == "A" * 20:
        assert selected[0]["chunk_id"] == "1" and selected[0]["context_kind"] == "chunk"


def test_pages_are_distinct_by_document_and_physical_page():
    context = pages({1: "First policy"})
    context.pages[("other.pdf", 1)] = "Second policy"
    selected = context.assemble([hit(1, "First", 1), hit(1, "Second", 2, document="other.pdf")],
                                max_sources=5, max_chars=500)
    assert len(selected) == 2
    assert selected[0]["chunk_id"] != selected[1]["chunk_id"]


@pytest.mark.parametrize("bad", [hit(2, "rule", 1), hit(1, "invented", 1)])
def test_wrong_page_or_seed_text_is_rejected(bad):
    with pytest.raises(IndexErrorBase, match="original PDF page"):
        pages({1: "Real rule"}).assemble([bad], max_sources=5, max_chars=500)


def test_page_loader_rejects_changed_corpus_before_and_after_extraction(monkeypatch):
    import retrieval_context
    with pytest.raises(IndexErrorBase, match="before"):
        PageContext(DOCUMENTS_DIR, {})
    fingerprints = pdf_fingerprints(DOCUMENTS_DIR)
    responses = iter([fingerprints, {}])
    monkeypatch.setattr(retrieval_context, "pdf_fingerprints", lambda path: next(responses))
    with pytest.raises(IndexErrorBase, match="during"):
        PageContext(DOCUMENTS_DIR, fingerprints)


def test_page_retrieval_reuses_index_embeds_once_and_records_both_contexts(indexed):
    documents, index, settings, _, provider, _ = indexed
    changed = replace(settings, top_k=5, retrieval_mode="pages", context_max_chars=3000)
    assert index_signature(documents, changed) == index_signature(documents, settings)
    retriever = Retriever(changed, index_dir=index, documents_dir=documents, embeddings=provider)
    try:
        result = retriever.retrieve("What approvals and deadlines apply?")
        assert result["search_k"] == 15
        assert len(result["ranked_chunks"]) == 15
        chunks = result["retrieved_chunks"]
        assert 1 <= len(chunks) <= 5
        assert len({(c["source_file"], c["page"]) for c in chunks}) == len(chunks)
        assert result["context_chars"] == sum(len(c["text"]) for c in chunks) <= 3000
        assert provider.query_calls == 1 and provider.document_calls == 1
        for c in chunks:
            raw = result["ranked_chunks"][c["seed_rank"] - 1]
            assert c["seed_chunk_id"] == raw["chunk_id"]
            if c["context_kind"] == "page":
                assert c["text"] == retriever.page_context.pages[(c["source_file"], c["page"])]
    finally:
        retriever.close()


def test_assembled_page_evidence_reaches_generation_and_keeps_real_provenance():
    selected = pages({1: "Register within three days after delivery."}).assemble(
        [hit(1, "Register", 1)], max_sources=5, max_chars=500)
    retriever = FakeRetriever(selected)
    retriever.top_k = 5
    raw = json.dumps({"answerable": True, "claims": [{"text": "Register within three days after delivery.",
                      "evidence": [{"source_id": "S1", "quote": "three days after delivery"}]}]})
    client = FakeClaude(raw)
    result = RAGAssistant(retriever, client).answer("What is the deadline?")
    assert len(retriever.questions) == len(client.requests) == 1
    assert result["sources"][0]["page"] == 1
    assert result["sources"][0]["document"] == "policy.pdf"
    assert result["sources"][0]["chunk_id"] == selected[0]["chunk_id"]
    assert result["sources"][0]["excerpt"] == "three days after delivery"
    assert json.loads(client.requests[0][0])["sources"][0]["text"] == selected[0]["text"]
    with pytest.raises(AnswerValidationError):
        validate_answer(raw.replace("three days after delivery", "five days after delivery"), selected, max_sources=5)


def test_evaluation_annotations_never_enter_page_context_prompt():
    selected = pages({1: "Actual policy"}).assemble([hit(1, "Actual", 1)], max_sources=5, max_chars=500)
    selected[0].update(expected_answer="DO_NOT_SEND", grading_criteria="DO_NOT_SEND")
    prompt = build_prompt("Question", selected, max_sources=5)
    assert "DO_NOT_SEND" not in prompt
    assert set(json.loads(prompt)) == {"question", "sources"}


@pytest.mark.parametrize("options", [{"retrieval_mode": "other"}, {"retrieval_mode": None},
                                    {"context_max_chars": 799}, {"context_max_chars": 20001},
                                    {"context_max_chars": True}, {"context_max_chars": 800.5}])
def test_invalid_context_settings_are_rejected(options):
    with pytest.raises(ConfigurationError):
        Settings(**options)


def test_new_settings_follow_existing_precedence_without_changing_baseline(tmp_path, monkeypatch):
    for name in ("RAG_RETRIEVAL_MODE", "RAG_CONTEXT_MAX_CHARS", "RAG_TOP_K"):
        monkeypatch.delenv(name, raising=False)
    missing = tmp_path / ".env"
    baseline = load_settings(env_file=missing)
    assert (baseline.retrieval_mode, baseline.top_k) == ("chunks", 3)
    missing.write_text("RAG_RETRIEVAL_MODE=pages\nRAG_TOP_K=5\nRAG_CONTEXT_MAX_CHARS=4000\n", encoding="utf-8")
    assert load_settings(env_file=missing).context_max_chars == 4000
    monkeypatch.setenv("RAG_CONTEXT_MAX_CHARS", "6000")
    settings = load_settings(env_file=missing, secrets={"RAG_CONTEXT_MAX_CHARS": 5000})
    assert settings.context_max_chars == 6000 and settings.retrieval_mode == "pages" and settings.top_k == 5
