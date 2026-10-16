"""Bounded, page-scoped context assembled without another embedding/search call."""

import hashlib
import json
from pathlib import Path

from config import pdf_fingerprints
from index_store import IndexErrorBase
from ingest import extract_pages


class PageContext:
    """Read the exact indexed corpus once; keep physical pages and text intact."""

    def __init__(self, documents_dir: Path, expected_fingerprints: dict):
        if pdf_fingerprints(documents_dir) != expected_fingerprints:
            raise IndexErrorBase("PDFs changed before page-context loading. Reload the index.")
        pages, _ = extract_pages(documents_dir)
        if pdf_fingerprints(documents_dir) != expected_fingerprints:
            raise IndexErrorBase("PDFs changed during page-context loading. Reload the index.")
        self.pages = {(p.metadata["source_file"], p.metadata["page"]): p.page_content for p in pages}

    def assemble(self, ranked_chunks: list[dict], *, max_sources: int, max_chars: int) -> list[dict]:
        """Use distinct pages in hit order, falling back to whole seed chunks.

        Never clip a page/chunk to fit. A non-fitting seed can be skipped so a
        later complete source still fits. All hits remain in the retrieval log.
        """
        selected, used_pages, used_chars = [], set(), 0
        for rank, chunk in enumerate(ranked_chunks, start=1):
            key = (chunk["source_file"], chunk["page"])
            page_text = self.pages.get(key)
            if page_text is None or "".join(chunk["text"].split()) not in "".join(page_text.split()):
                raise IndexErrorBase("Retrieved chunk does not match its original PDF page. Reload the index.")
            if key in used_pages or len(selected) >= max_sources:
                continue
            available = max_chars - used_chars
            text = page_text if len(page_text) <= available else chunk["text"]
            if len(text) > available:
                continue
            is_page = text == page_text
            identity = hashlib.sha256(json.dumps([*key, text], ensure_ascii=False).encode("utf-8")).hexdigest()
            selected.append({
                **chunk, "source_id": f"S{len(selected) + 1}", "text": text,
                "chunk_id": f"page:{identity}" if is_page else chunk["chunk_id"],
                "context_kind": "page" if is_page else "chunk",
                "seed_chunk_id": chunk["chunk_id"], "seed_rank": rank,
            })
            used_pages.add(key)
            used_chars += len(text)
        return selected
