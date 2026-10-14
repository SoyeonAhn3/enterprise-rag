"""Offline ingestion checks against the actual corpus and failure fixtures."""

import json
from pathlib import Path
import socket
import subprocess
import sys

from langchain_core.documents import Document
import pymupdf
import pytest

from config import CHUNK_SIZE, PROJECT_ROOT
from ingest import IngestionError, main, prepare_corpus, split_pages


def normalize(text: str) -> str:
    """Ignore PDF layout whitespace, including line breaks inside Korean words.

    Preserve every non-whitespace character so changed amounts, punctuation,
    and negation still fail the reference-quote check.
    """
    return "".join(text.split())


def write_pdf(path: Path, texts: list[str], **save_options) -> None:
    with pymupdf.open() as pdf:
        for text in texts:
            page = pdf.new_page()
            if text:
                page.insert_text((72, 72), text)
        pdf.save(path, **save_options)


@pytest.fixture(scope="module")
def corpus():
    return prepare_corpus()


def test_runtime_files_match_the_reviewed_source_materials():
    originals = PROJECT_ROOT / "rag_mvp_sample_documents"
    runtime_pdfs = sorted((PROJECT_ROOT / "documents").glob("*.pdf"))
    assert {path.name for path in runtime_pdfs} == {path.name for path in originals.glob("*.pdf")}
    for path in runtime_pdfs:
        assert path.read_bytes() == (originals / path.name).read_bytes(), path.name
    assert (PROJECT_ROOT / "eval/questions.json").read_bytes() == (originals / "eval/questions.json").read_bytes()


def test_corpus_preserves_all_physical_pages_and_chunk_sources(corpus):
    assert corpus.document_page_counts == {
        "01_purchase_process.pdf": 3,
        "02_approval_budget.pdf": 3,
        "03_it_security.pdf": 3,
        "04_contract_settlement.pdf": 4,
    }
    assert corpus.summary["text_pages"] == 13
    assert corpus.summary["skipped_pages"] == 0
    page_texts = {
        (page.metadata["source_file"], page.metadata["page"]): page.page_content
        for page in corpus.pages
    }
    covered_pages = set()
    ids = []
    for chunk in corpus.chunks:
        source = (chunk.metadata["source_file"], chunk.metadata["page"])
        assert 0 < len(chunk.page_content) <= CHUNK_SIZE
        assert normalize(chunk.page_content) in normalize(page_texts[source])
        assert chunk.id == chunk.metadata["chunk_id"]
        covered_pages.add(source)
        ids.append(chunk.id)
    assert len(ids) == len(set(ids))
    assert covered_pages == set(page_texts)
    for name, count in corpus.document_page_counts.items():
        assert {page for source, page in covered_pages if source == name} == set(range(1, count + 1))


QUESTIONS = json.loads((PROJECT_ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("question", QUESTIONS, ids=lambda question: question["id"])
def test_eval_reference_quotes_exist_in_their_declared_pdf_pages(corpus, question):
    # This checks fixture integrity, not retrieval or answer quality.
    if not question["answerable"]:
        assert question["evidence_groups"] == []
        return
    assert question["evidence_groups"]
    pages = {
        (page.metadata["source_file"], page.metadata["page"]): normalize(page.page_content)
        for page in corpus.pages
    }
    for group in question["evidence_groups"]:
        assert group["any_of"]
        for candidate in group["any_of"]:
            source = (candidate["document"], candidate["page"])
            assert source in pages
            quote = normalize(candidate["quote"])
            assert quote and quote in pages[source], (question["id"], source)


@pytest.mark.parametrize("question_id, before, after", [
    ("q01", "100만원", "101만원"),
    ("q04", "필요하다", "불필요하다"),
])
def test_quote_verification_rejects_changed_amounts_and_negation(corpus, question_id, before, after):
    question = next(item for item in QUESTIONS if item["id"] == question_id)
    candidate = question["evidence_groups"][0]["any_of"][0]
    page = next(
        item for item in corpus.pages
        if item.metadata["source_file"] == candidate["document"] and item.metadata["page"] == candidate["page"]
    )
    assert before in candidate["quote"]
    changed_quote = candidate["quote"].replace(before, after)
    assert normalize(candidate["quote"]) in normalize(page.page_content)
    assert normalize(changed_quote) not in normalize(page.page_content)


def test_ids_are_repeatable_and_distinguish_page_source_and_changed_text(corpus):
    assert [chunk.id for chunk in prepare_corpus().chunks] == [chunk.id for chunk in corpus.chunks]
    pages = [
        Document(page_content="Approval required.", metadata={"source_file": "a.pdf", "page": 1}),
        Document(page_content="Approval required.", metadata={"source_file": "a.pdf", "page": 2}),
        Document(page_content="Approval required.", metadata={"source_file": "b.pdf", "page": 1}),
        Document(page_content="Approval waived.", metadata={"source_file": "a.pdf", "page": 1}),
    ]
    assert len({chunk.id for chunk in split_pages(pages)}) == 4


def test_blank_pages_are_skipped_without_renumbering(tmp_path):
    write_pdf(tmp_path / "with_blank_pages.pdf", ["", "Approval on physical page two.", ""])
    result = prepare_corpus(tmp_path)
    assert result.summary["total_pages"] == 3
    assert result.summary["skipped_pages"] == 2
    assert {chunk.metadata["page"] for chunk in result.chunks} == {2}


def test_only_top_level_pdfs_enter_the_corpus(tmp_path):
    write_pdf(tmp_path / "policy.PDF", ["Registered policy text."])
    (tmp_path / "questions.json").write_text('{"answer": "EVALUATION_ONLY"}', encoding="utf-8")
    (tmp_path / "README.md").write_text("EVALUATION_ONLY", encoding="utf-8")
    nested = tmp_path / "eval"
    nested.mkdir()
    write_pdf(nested / "answers.pdf", ["EVALUATION_ONLY"])
    result = prepare_corpus(tmp_path)
    assert set(result.document_page_counts) == {"policy.PDF"}
    assert all("EVALUATION_ONLY" not in chunk.page_content for chunk in result.chunks)


@pytest.mark.parametrize("kind", ["missing", "empty", "corrupt", "zero_byte", "mixed_corrupt", "blank", "encrypted"])
def test_unusable_corpora_fail_explicitly(tmp_path, kind):
    source = tmp_path
    if kind == "missing":
        source = tmp_path / "missing"
    elif kind in {"corrupt", "mixed_corrupt"}:
        (tmp_path / "broken.pdf").write_bytes(b"not a PDF")
        if kind == "mixed_corrupt":
            write_pdf(tmp_path / "a_valid.pdf", ["Valid policy."])
    elif kind == "zero_byte":
        (tmp_path / "empty.pdf").write_bytes(b"")
    elif kind == "blank":
        write_pdf(tmp_path / "blank.pdf", [""])
    elif kind == "encrypted":
        write_pdf(
            tmp_path / "protected.pdf", ["Private text."],
            encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="test-owner", user_pw="test-user",
        )
    with pytest.raises(IngestionError):
        prepare_corpus(source)


@pytest.mark.parametrize("size, overlap", [(0, 0), (-1, 0), (100, -1), (100, 100), (100, 101)])
def test_invalid_chunk_settings_are_rejected(size, overlap):
    with pytest.raises(IngestionError):
        split_pages([], chunk_size=size, chunk_overlap=overlap)


def test_cli_works_outside_project_directory_and_writes_valid_preview(tmp_path):
    output = tmp_path / "preview.json"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ingest.py"), "--dry-run", "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    preview = json.loads(output.read_text(encoding="utf-8"))
    assert preview["summary"]["documents"] == 4
    assert preview["summary"]["text_pages"] == 13
    assert len(preview["chunks"]) == preview["summary"]["chunks"]
    assert "No embeddings, index, or API requests" in result.stdout


def test_cli_requires_dry_run_for_preview_output(tmp_path):
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ingest.py"), "--output", str(tmp_path / "preview.json")],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "--output requires --dry-run" in result.stderr


@pytest.mark.parametrize("kind", ["missing", "invalid_chunk", "unwritable_output"])
def test_cli_returns_failure_and_preserves_existing_output(tmp_path, kind):
    output = tmp_path / "preview.json"
    previous_output = "previous successful preview"
    output.write_text(previous_output, encoding="utf-8")
    arguments = ["--documents", str(tmp_path / "missing")] if kind == "missing" else []
    if kind == "invalid_chunk":
        arguments = ["--chunk-size", "120", "--chunk-overlap", "120"]
    output_target = output
    if kind == "unwritable_output":
        output_target = tmp_path / "directory.json"
        output_target.mkdir()
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "ingest.py"), "--dry-run", "--output", str(output_target), *arguments],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1
    assert "Ingestion failed:" in result.stderr
    assert "Traceback" not in result.stderr
    assert output.read_text(encoding="utf-8") == previous_output
    assert "Dry run complete" not in result.stdout


def test_dry_run_needs_no_credentials_or_network(tmp_path, monkeypatch):
    for name in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2"):
        monkeypatch.delenv(name, raising=False)

    def reject_network(*args, **kwargs):
        raise AssertionError("Offline ingestion attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", reject_network)
    monkeypatch.setattr(socket.socket, "connect_ex", reject_network)
    monkeypatch.setattr(socket, "create_connection", reject_network)
    monkeypatch.setattr(socket, "getaddrinfo", reject_network)
    output = tmp_path / "offline.json"
    assert main(["--dry-run", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["documents"] == 4
