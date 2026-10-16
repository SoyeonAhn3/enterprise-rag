"""Bounded, page-scoped context assembled without another embedding/search call."""

import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata

from config import pdf_fingerprints
from index_store import IndexErrorBase
from ingest import extract_pages

PAGE_SELECTION_POLICY = "rank_with_coverage_slot_v1"


def query_features(text: str) -> set[str]:
    """Lightweight lexical features, not reference answers or semantic claims.

    Korean character pairs tolerate suffixes without a tokenizer dependency;
    other words match case-insensitively. Never alter text used for citations.
    """
    features = set()
    for word in re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", text).casefold()):
        if re.search(r"[가-힣]", word):
            features.update(word[i:i + 2] for i in range(len(word) - 1))
        elif len(word) > 1:
            features.add(word)
    return features


def _source(chunk, rank, text, page_text, position):
    is_page = text == page_text
    identity = hashlib.sha256(json.dumps(
        [chunk["source_file"], chunk["page"], text], ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    return {
        **chunk, "source_id": f"S{position}", "text": text,
        "chunk_id": f"page:{identity}" if is_page else chunk["chunk_id"],
        "context_kind": "page" if is_page else "chunk",
        "seed_chunk_id": chunk["chunk_id"], "seed_rank": rank,
    }


class PageContext:
    """Read the exact indexed corpus once; keep physical pages and text intact."""

    def __init__(self, documents_dir: Path, expected_fingerprints: dict):
        if pdf_fingerprints(documents_dir) != expected_fingerprints:
            raise IndexErrorBase("PDFs changed before page-context loading. Reload the index.")
        pages, _ = extract_pages(documents_dir)
        if pdf_fingerprints(documents_dir) != expected_fingerprints:
            raise IndexErrorBase("PDFs changed during page-context loading. Reload the index.")
        self.pages = {(p.metadata["source_file"], p.metadata["page"]): p.page_content for p in pages}

    def assemble(self, ranked_chunks: list[dict], *, max_sources: int, max_chars: int,
                 question: str = "") -> list[dict]:
        """Use distinct pages in hit order, falling back to whole seed chunks.

        Never clip a page/chunk to fit. A non-fitting seed can be skipped so a
        later complete source still fits. All hits remain in the retrieval log.
        With a question, only the final slot may move to improve query coverage.
        An empty question explicitly reproduces the original rank-only selector.
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
            selected.append(_source(chunk, rank, text, page_text, len(selected) + 1))
            used_pages.add(key)
            used_chars += len(text)
        if question and max_sources > 1 and len(selected) == max_sources:
            selected = self._coverage_slot(selected, ranked_chunks, question, max_chars)
        return selected

    def _coverage_slot(self, selected, ranked_chunks, question, max_chars):
        """Preserve the prefix and all unique query features of the old last slot.

        A replacement must strictly add weighted uncovered query features. IDF
        weights use distinct candidate pages only. Ties keep the earlier hit.
        This lexical safeguard does not guarantee semantic answer completeness.
        """
        wanted = query_features(question)
        prefix = selected[:-1]
        covered = set().union(*(query_features(c["text"]) for c in prefix)) & wanted
        candidate_pages = {(c["source_file"], c["page"]) for c in ranked_chunks}
        page_features = [query_features(self.pages[key]) & wanted for key in candidate_pages]
        weights = {term: 1 + math.log((1 + len(page_features)) /
                                     (1 + sum(term in f for f in page_features))) for term in wanted}
        required = (query_features(selected[-1]["text"]) & wanted) - covered
        score = lambda features: sum(weights[f] for f in sorted(features))
        best_score, best = score(required), selected[-1]
        used = {(c["source_file"], c["page"]) for c in prefix}
        available = max_chars - sum(len(c["text"]) for c in prefix)
        seen = set(used)
        for rank, chunk in enumerate(ranked_chunks, start=1):
            key = (chunk["source_file"], chunk["page"])
            if key in seen:
                continue
            page_text = self.pages[key]
            text = page_text if len(page_text) <= available else chunk["text"]
            if len(text) > available:
                continue
            seen.add(key)
            added = (query_features(text) & wanted) - covered
            gain = score(added)
            if required <= added and gain > best_score:
                best_score = gain
                best = _source(chunk, rank, text, page_text, len(selected))
        if best is not selected[-1]:
            best["selection_reason"] = "additional_query_coverage"
            best["replaced_seed_rank"] = selected[-1]["seed_rank"]
            return [*prefix, best]
        return selected
