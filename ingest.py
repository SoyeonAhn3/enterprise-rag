"""Build a fixed PDF index, or preview page-scoped chunks with --dry-run."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import sys

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import pymupdf

from config import CHUNK_OVERLAP, CHUNK_SIZE, ConfigurationError, DOCUMENTS_DIR, INDEX_DIR, PREVIEW_PATH, load_settings, pdf_fingerprints


class IngestionError(ValueError):
    """A document or chunk setting cannot be used for ingestion."""


@dataclass
class PreparedCorpus:
    pages: list[Document]
    chunks: list[Document]
    document_page_counts: dict[str, int]
    source_fingerprints: dict[str, str]
    chunk_size: int
    chunk_overlap: int

    @property
    def summary(self) -> dict[str, int]:
        total_pages = sum(self.document_page_counts.values())
        return {
            "documents": len(self.document_page_counts),
            "total_pages": total_pages,
            "text_pages": len(self.pages),
            "skipped_pages": total_pages - len(self.pages),
            "chunks": len(self.chunks),
        }


def extract_pages(documents_dir: Path) -> tuple[list[Document], dict[str, int]]:
    """Read only immediate PDF children, retaining physical 1-based pages."""
    if not documents_dir.is_dir():
        raise IngestionError(f"Document directory does not exist: {documents_dir}")

    pdf_paths = sorted(
        (path for path in documents_dir.iterdir()
         if path.is_file() and path.suffix.lower() == ".pdf"),
        key=lambda path: path.name,
    )
    if not pdf_paths:
        raise IngestionError(f"No PDF files found in: {documents_dir}")

    pages = []
    page_counts = {}
    for path in pdf_paths:
        first_page = len(pages)
        try:
            with pymupdf.open(path) as pdf:
                if not pdf.is_pdf:
                    raise IngestionError(f"Not a PDF document: {path.name}")
                if pdf.needs_pass:
                    raise IngestionError(f"Password-protected PDF: {path.name}")
                page_counts[path.name] = len(pdf)
                for number, page in enumerate(pdf, start=1):
                    # This corpus's text order was reviewed. Do not flatten
                    # line breaks or merge pages before splitting.
                    text = page.get_text("text").strip()
                    if text:
                        pages.append(Document(
                            page_content=text,
                            metadata={"source_file": path.name, "page": number},
                        ))
        except (pymupdf.FileDataError, RuntimeError, OSError) as exc:
            raise IngestionError(f"Could not read PDF: {path.name}") from exc

        if len(pages) == first_page:
            raise IngestionError(
                f"No extractable text in {path.name}; scanned PDFs require OCR "
                "and are outside this MVP."
            )
    return pages, page_counts


def split_pages(
    pages: list[Document],
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """Split each page separately and give every chunk a stable content ID."""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise IngestionError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = []
    for page in pages:
        for position, text in enumerate(splitter.split_text(page.page_content)):
            identity = json.dumps(
                [page.metadata["source_file"], page.metadata["page"], position, text],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            chunk_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()
            chunks.append(Document(
                id=chunk_id,
                page_content=text,
                metadata={**page.metadata, "chunk_id": chunk_id},
            ))
    return chunks


def prepare_corpus(
    documents_dir: Path = DOCUMENTS_DIR,
    *,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> PreparedCorpus:
    try:
        before = pdf_fingerprints(documents_dir)
    except OSError:
        raise IngestionError(f"Could not read document directory: {documents_dir}") from None
    pages, page_counts = extract_pages(documents_dir)
    chunks = split_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if before != pdf_fingerprints(documents_dir):
        raise IngestionError("PDFs changed during preparation. Run ingestion again.")
    return PreparedCorpus(pages, chunks, page_counts, before, chunk_size, chunk_overlap)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Extract and preview; no API calls.")
    parser.add_argument("--documents", type=Path, default=DOCUMENTS_DIR)
    parser.add_argument("--output", type=Path, help="Preview output; requires --dry-run.")
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--rebuild", action="store_true", help="Build and activate a new index collection.")
    parser.add_argument("--chunk-size", type=int)
    parser.add_argument("--chunk-overlap", type=int)
    args = parser.parse_args(argv)
    if args.output is not None and not args.dry_run:
        parser.error("--output requires --dry-run.")
    if args.dry_run and args.rebuild:
        parser.error("--dry-run cannot be combined with --rebuild.")

    try:
        if not args.dry_run:
            from embeddings import EmbeddingError
            from index_store import IndexErrorBase, build_index

            settings = load_settings()
            overrides = {}
            if args.chunk_size is not None:
                overrides["chunk_size"] = args.chunk_size
            if args.chunk_overlap is not None:
                overrides["chunk_overlap"] = args.chunk_overlap
            settings = replace(settings, **overrides)
            corpus = prepare_corpus(args.documents, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
            try:
                result = build_index(corpus, args.index_dir, args.documents, settings, rebuild=args.rebuild)
            except (IndexErrorBase, EmbeddingError) as exc:
                raise IngestionError(str(exc)) from None
            except ConfigurationError:
                raise
            except Exception:
                raise IngestionError("Could not complete Chroma indexing. Check local storage and retry with --rebuild.") from None
            print(json.dumps({**corpus.summary, **result}))
            print(f"Index {result['action']} at {args.index_dir}")
            return 0

        chunk_size = args.chunk_size if args.chunk_size is not None else CHUNK_SIZE
        chunk_overlap = args.chunk_overlap if args.chunk_overlap is not None else CHUNK_OVERLAP
        corpus = prepare_corpus(
            args.documents, chunk_size=chunk_size, chunk_overlap=chunk_overlap,
        )
        preview = {
            "schema_version": 1,
            "chunking": {"chunk_size": chunk_size, "chunk_overlap": chunk_overlap},
            "summary": corpus.summary,
            "documents": corpus.document_page_counts,
            "chunks": [
                {"page_content": chunk.page_content, "metadata": chunk.metadata}
                for chunk in corpus.chunks
            ],
        }
        output = args.output or PREVIEW_PATH
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    except (IngestionError, ConfigurationError, OSError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(corpus.summary))
    print(f"Preview written to {output}")
    print("Dry run complete. No embeddings, index, or API requests were created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
