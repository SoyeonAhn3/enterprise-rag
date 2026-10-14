from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from config import DOCUMENTS_DIR, PROJECT_ROOT, Settings
from embeddings import EmbeddingError
import index_store
from index_store import IndexErrorBase, build_index, load_index
from ingest import prepare_corpus
from rag import Retriever
from tests.fakes import CountingEmbeddings


@pytest.fixture
def workspace(tmp_path):
    documents = tmp_path / "documents"
    documents.mkdir()
    for path in DOCUMENTS_DIR.glob("*.pdf"):
        shutil.copyfile(path, documents / path.name)
    settings = Settings(embedding_model="test-only-deterministic", embedding_dimensions=16)
    return documents, tmp_path / "index", settings


@pytest.fixture
def indexed(workspace):
    documents, index, settings = workspace
    provider = CountingEmbeddings()
    corpus = prepare_corpus(documents)
    result = build_index(corpus, index, documents, settings, embeddings=provider)
    return documents, index, settings, corpus, provider, result


def test_real_chroma_roundtrip_reuses_index_and_only_embeds_queries(indexed):
    documents, index, settings, corpus, provider, first = indexed
    assert provider.document_calls == 1
    assert provider.document_count == 22
    second = build_index(corpus, index, documents, settings, embeddings=provider)
    assert second["action"] == "reused"
    assert second["collection"] == first["collection"]
    assert provider.document_calls == 1
    retriever = Retriever(settings, index_dir=index, documents_dir=documents, embeddings=provider)
    try:
        questions = json.loads((PROJECT_ROOT / "eval/questions.json").read_text(encoding="utf-8"))
        for item in (question for question in questions if question["id"] in {"q01", "q07", "q08"}):
            result = retriever.retrieve(item["question"])
            assert len(result["retrieved_chunks"]) == 3
            assert [chunk["source_id"] for chunk in result["retrieved_chunks"]] == ["S1", "S2", "S3"]
            for chunk in result["retrieved_chunks"]:
                original = next(original for original in corpus.chunks if original.id == chunk["chunk_id"])
                assert chunk["text"] == original.page_content
                assert chunk["source_file"] == original.metadata["source_file"]
                assert chunk["page"] == original.metadata["page"]
            assert result["retrieval_latency_ms"] >= 0
        assert provider.query_calls == 3
        assert provider.document_calls == 1
    finally:
        retriever.close()


def test_new_process_reloads_without_reembedding(indexed):
    documents, index, settings, *_ = indexed
    code = """
import json, sys
from pathlib import Path
from config import Settings
from rag import Retriever
from tests.fakes import CountingEmbeddings
provider = CountingEmbeddings(fail_documents=True)
retriever = Retriever(Settings(embedding_model='test-only-deterministic', embedding_dimensions=16), index_dir=Path(sys.argv[1]), documents_dir=Path(sys.argv[2]), embeddings=provider)
try:
    result = retriever.retrieve('Who approves the purchase?')
    print(json.dumps({'chunks': len(result['retrieved_chunks']), 'document_calls': provider.document_calls, 'query_calls': provider.query_calls}))
finally:
    retriever.close()
"""
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", code, str(index), str(documents)], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"chunks": 3, "document_calls": 0, "query_calls": 1}


@pytest.mark.parametrize("change", ["model", "dimensions", "chunk_size", "overlap", "pdf", "removed_pdf"])
def test_stale_index_is_rejected_before_query_calls(indexed, change):
    documents, index, settings, _, provider, _ = indexed
    if change == "model":
        settings = replace(settings, embedding_model="different-model")
    elif change == "dimensions":
        settings = replace(settings, embedding_dimensions=8)
    elif change == "chunk_size":
        settings = replace(settings, chunk_size=700)
    elif change == "overlap":
        settings = replace(settings, chunk_overlap=100)
    elif change == "pdf":
        path = next(documents.glob("*.pdf"))
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        next(documents.glob("*.pdf")).unlink()
    with pytest.raises(IndexErrorBase, match="does not match"):
        Retriever(settings, index_dir=index, documents_dir=documents, embeddings=provider)
    assert provider.query_calls == 0


def test_rebuild_activates_only_the_current_corpus(indexed):
    documents, index, settings, _, provider, first = indexed
    removed = documents / "04_contract_settlement.pdf"
    removed.unlink()
    corpus = prepare_corpus(documents)
    result = build_index(corpus, index, documents, settings, rebuild=True, embeddings=provider)
    assert result["collection"] != first["collection"]
    assert result["chunk_count"] == len(corpus.chunks) == 16
    loaded = load_index(index, documents, settings, embeddings=provider)
    try:
        records = loaded.store.get()
        assert len(records["ids"]) == len(set(records["ids"])) == 16
        assert all(item["source_file"] != removed.name for item in records["metadatas"])
    finally:
        loaded.close()


@pytest.mark.parametrize("failure", ["provider", "manifest_write"])
def test_failed_rebuild_preserves_previous_active_index(indexed, monkeypatch, failure):
    documents, index, settings, corpus, _, _ = indexed
    before = (index / "manifest.json").read_bytes()
    provider = CountingEmbeddings(fail_documents=failure == "provider")
    if failure == "manifest_write":
        def fail(*args):
            raise OSError("simulated manifest write failure")
        monkeypatch.setattr(index_store, "_activate_manifest", fail)
    with pytest.raises((EmbeddingError, OSError)):
        build_index(corpus, index, documents, settings, rebuild=True, embeddings=provider)
    assert (index / "manifest.json").read_bytes() == before
    retriever = Retriever(settings, index_dir=index, documents_dir=documents, embeddings=CountingEmbeddings())
    try:
        assert len(retriever.retrieve("approval")['retrieved_chunks']) == 3
    finally:
        retriever.close()


@pytest.mark.parametrize("damage", ["missing_manifest", "malformed_manifest", "missing_collection", "deleted_chunk", "modified_metadata"])
def test_missing_or_corrupt_index_fails_without_silent_creation(indexed, damage):
    documents, index, settings, _, provider, _ = indexed
    manifest_path = index / "manifest.json"
    if damage == "missing_manifest":
        manifest_path.unlink()
    elif damage == "malformed_manifest":
        manifest_path.write_text("not JSON", encoding="utf-8")
    else:
        loaded = load_index(index, documents, settings, embeddings=provider)
        try:
            collection = loaded.client.get_collection(loaded.manifest["collection"], embedding_function=None)
            chunk_id = collection.get()["ids"][0]
            if damage == "missing_collection":
                loaded.client.delete_collection(loaded.manifest["collection"])
            elif damage == "deleted_chunk":
                collection.delete(ids=[chunk_id])
            else:
                collection.update(ids=[chunk_id], metadatas=[{"page": 999}])
        finally:
            loaded.close()
    with pytest.raises(IndexErrorBase):
        load_index(index, documents, settings, embeddings=provider)
    assert provider.document_calls == 1
    assert provider.query_calls == 0


def test_missing_index_does_not_create_storage(workspace):
    documents, index, settings = workspace
    with pytest.raises(IndexErrorBase):
        load_index(index, documents, settings, embeddings=CountingEmbeddings())
    assert not index.exists()


@pytest.mark.parametrize("changed_field,value", [("provider", "openai"), ("adapter_version", 0)])
def test_different_embedding_provider_or_adapter_requires_rebuild(indexed, changed_field, value):
    documents, index, settings, _, provider, _ = indexed
    path = index / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["signature"]["embedding"][changed_field] = value
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(IndexErrorBase, match="does not match"):
        load_index(index, documents, settings, embeddings=provider)
    assert provider.query_calls == 0


def test_claude_settings_do_not_invalidate_or_load_local_embedding_model(indexed, monkeypatch):
    documents, index, settings, corpus, _, first = indexed

    def unexpected_model_load(*args, **kwargs):
        raise AssertionError("Index reuse must not load the embedding model")

    monkeypatch.setattr(index_store, "create_embeddings", unexpected_model_load)
    changed = replace(settings, anthropic_api_key="new-test-key", chat_model="another-claude-model", chat_max_tokens=512)
    result = build_index(corpus, index, documents, changed)
    assert result["action"] == "reused"
    assert result["collection"] == first["collection"]


@pytest.mark.parametrize("question", ["", "   ", "x" * 501])
def test_invalid_questions_make_no_embedding_calls(indexed, question):
    documents, index, settings, _, provider, _ = indexed
    retriever = Retriever(settings, index_dir=index, documents_dir=documents, embeddings=provider)
    try:
        with pytest.raises(ValueError):
            retriever.retrieve(question)
        assert provider.query_calls == 0
    finally:
        retriever.close()


def test_query_provider_failure_is_not_an_empty_successful_result(indexed):
    documents, index, settings, *_ = indexed
    retriever = Retriever(settings, index_dir=index, documents_dir=documents, embeddings=CountingEmbeddings(fail_query=True))
    try:
        with pytest.raises(EmbeddingError):
            retriever.retrieve("approval")
    finally:
        retriever.close()


@pytest.mark.parametrize("change", ["pdf", "chunk_settings"])
def test_prepared_snapshot_cannot_be_labeled_as_a_different_input(workspace, change):
    documents, index, settings = workspace
    corpus = prepare_corpus(documents)
    if change == "pdf":
        path = next(documents.glob("*.pdf"))
        path.write_bytes(path.read_bytes() + b"\n")
    else:
        settings = replace(settings, chunk_size=700)
    provider = CountingEmbeddings()
    with pytest.raises(IndexErrorBase, match="Prepared corpus"):
        build_index(corpus, index, documents, settings, embeddings=provider)
    assert provider.document_calls == 0
    assert not index.exists()


def test_input_change_during_embedding_does_not_activate_new_index(indexed):
    documents, index, settings, corpus, provider, _ = indexed
    previous = (index / "manifest.json").read_bytes()
    original_embed = provider.embed_documents

    def changing_embed(texts):
        path = next(documents.glob("*.pdf"))
        path.write_bytes(path.read_bytes() + b"\n")
        return original_embed(texts)

    provider.embed_documents = changing_embed
    with pytest.raises(IndexErrorBase, match="PDFs changed during indexing"):
        build_index(corpus, index, documents, settings, rebuild=True, embeddings=provider)
    assert (index / "manifest.json").read_bytes() == previous


def test_first_failed_build_can_be_retried_with_explicit_rebuild(workspace):
    documents, index, settings = workspace
    corpus = prepare_corpus(documents)
    with pytest.raises(EmbeddingError):
        build_index(corpus, index, documents, settings, embeddings=CountingEmbeddings(fail_documents=True))
    assert not (index / "manifest.json").exists()
    with pytest.raises(IndexErrorBase, match="--rebuild"):
        build_index(corpus, index, documents, settings, embeddings=CountingEmbeddings())
    result = build_index(corpus, index, documents, settings, rebuild=True, embeddings=CountingEmbeddings())
    assert result["action"] == "built"
    assert result["chunk_count"] == 22
    loaded = load_index(index, documents, settings, require_embeddings=False)
    loaded.close()
