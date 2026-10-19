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

PAGE_SELECTION_POLICY = "query_and_section_topics_v3"


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


def rule_topics(text: str) -> set[str]:
    """Normalize business-rule wording, without document IDs or amount rules.

    A policy assertion in the scenario also needs evidence, even when the last
    sentence asks a different question. Ordinary approval mentions alone do not
    imply that an authority table is needed.
    """
    compact = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())
    patterns = {
        "authority": r"(?:승인|결재|전결)(?:권자|권한|자|구간|라인)|approver|approval(?:authority|band|limit)",
        "budget": r"예산|budget",
        "quotation": r"견적|quotation|quotes?",
        "security": r"보안|security",
        "privacy": r"개인정보|privacy",
        "legal": r"법무|legal",
        "acceptance": r"검수|acceptance",
        "settlement": r"정산|settlement",
        "request_form": r"요청서|requestform",
    }
    return {"@" + name for name, pattern in patterns.items() if re.search(pattern, compact)}


def section_features(text: str) -> set[str]:
    """Features of numbered/Markdown section titles, never rewritten evidence."""
    titles = re.findall(r"(?m)^\s*(?:\d{1,3}[.)]|\#{1,6})\s+([^\n]{1,120})", text)
    headings = " ".join(titles)
    return query_features(headings) | rule_topics(headings)


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
        With a question, refine redundant slots while retaining the first hit
        and all query features already covered by the selected context.
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
            selected = self._refine_coverage(selected, ranked_chunks, question, max_chars)
        return selected

    def _refine_coverage(self, selected, ranked_chunks, question, max_chars):
        """Replace redundant non-leading slots; favor direct section coverage.

        Scores use only question/text, with IDF over distinct candidate pages.
        Preserve two leading semantic hits and all covered query/section terms.
        The last sentence focuses section matching on the actual request rather
        than preceding scenario details. Require new direct section coverage.
        This is a bounded lexical heuristic, not semantic completeness proof.
        """
        wanted = query_features(question) | rule_topics(question)
        request = re.split(r"[.!?。？！]\s+", question.strip())[-1]
        # Scenario facts (e.g. no personal data) are not extra rule requests.
        # A claimed approval role/band is a policy assertion that needs checking.
        focus = query_features(request) | rule_topics(request) | (rule_topics(question) & {"@authority"})
        if not wanted:
            return selected
        keys = {(c["source_file"], c["page"]) for c in ranked_chunks}
        features = [(query_features(self.pages[key]) | rule_topics(self.pages[key])) & wanted for key in keys]
        weights = {term: 1 + math.log((1 + len(features)) /
                                     (1 + sum(term in f for f in features))) for term in wanted}
        cache = {}

        def covered(text):
            if text not in cache:
                cache[text] = ((query_features(text) | rule_topics(text)) & wanted, section_features(text) & focus)
            return cache[text]

        def score(sources):
            words, titles = set(), set()
            for source in sources:
                plain, headings = covered(source["text"])
                words.update(plain)
                titles.update(headings)
            return words, titles, (sum(t.startswith("@") for t in titles),
                                   sum(weights[t] for t in sorted(titles)),
                                   sum(weights[t] for t in sorted(words)))

        # At most one accepted improvement per replaceable slot. No extra search.
        for _ in range(len(selected) - 1):
            required, required_titles, best_score = score(selected)
            best = None
            selected_keys = {(c["source_file"], c["page"]) for c in selected}
            for position in range(len(selected) - 1, min(2, len(selected) - 1) - 1, -1):
                available = max_chars - sum(len(c["text"]) for i, c in enumerate(selected) if i != position)
                seen = set(selected_keys)
                for rank, chunk in enumerate(ranked_chunks, 1):
                    key = (chunk["source_file"], chunk["page"])
                    if key in seen:
                        continue
                    page_text = self.pages[key]
                    text = page_text if len(page_text) <= available else chunk["text"]
                    if len(text) > available:
                        continue
                    # Different fallback chunks on the same page may be useful.
                    if text == page_text:
                        seen.add(key)
                    candidate = _source(chunk, rank, text, page_text, position + 1)
                    trial = [candidate if i == position else c for i, c in enumerate(selected)]
                    words, titles, value = score(trial)
                    # Whole rule topics outrank incidental Korean character-pair
                    # overlaps (e.g. 법무팀/재무팀 share 무팀). Keep every existing
                    # requested topic and literal non-Korean section term.
                    protected = {t for t in required_titles if not re.search(r"[가-힣]", t)}
                    topics_added = {t for t in titles - required_titles if t.startswith("@")}
                    retains_titles = required_titles <= titles or (topics_added and protected <= titles)
                    if (required <= words and retains_titles and titles - required_titles and value > best_score):
                        best_score = value
                        candidate.update(selection_reason="query_and_section_coverage",
                                         replaced_seed_rank=selected[position]["seed_rank"])
                        best = trial
            if best is None:
                break
            selected = best
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
