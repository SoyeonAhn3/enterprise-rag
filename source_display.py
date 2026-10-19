"""Conservative display formatting; retrieved text and verified quotes stay raw."""

from functools import lru_cache
from html import escape
import re

import pymupdf

from config import DOCUMENTS_DIR

_WORD = re.compile(r"[^\W_]+")
_SPLIT_WORD = re.compile(r"([^\W_]+)\n(?=([^\W_]+))")


def source_excerpts(result: dict, source: dict) -> list[str]:
    """Show every validated quote for this source, including saved answers.

    The legacy sources[].excerpt stores only the first quote. Claim evidence
    retains all quotes; prefer it without mutating the answer or its schema.
    Keep separate passages separate and remove whitespace-only duplicates.
    Older results without claim evidence still display their original excerpt.
    """
    excerpts, seen = [], set()
    for claim in result.get("claims", []):
        for evidence in claim["evidence"]:
            if evidence["source_id"] != source["source_id"]:
                continue
            quote = evidence["quote"]
            normalized = "".join(quote.split())
            if normalized not in seen:
                seen.add(normalized)
                excerpts.append(quote)
    return excerpts or [source["excerpt"]]


@lru_cache(maxsize=1)
def corpus_words() -> frozenset[str]:
    """Use only unbroken words in the fixed PDFs, never evaluation annotations.

    The application already requires a restart when the corpus changes. Reading
    these small PDFs once needs neither embeddings nor an additional API call.
    """
    words = set()
    for path in sorted(DOCUMENTS_DIR.glob("*.pdf")):
        try:
            with pymupdf.open(path) as pdf:
                for page in pdf:
                    words.update(_WORD.findall(page.get_text("text")))
        except (OSError, RuntimeError, ValueError):
            # Formatting must not prevent an already validated answer displaying.
            continue
    return frozenset(words)


def readable_excerpt(text: str) -> str:
    """Reconnect a PDF-split word only when that full word exists in the corpus.

    Existing spaces, paragraph/list boundaries, and unknown splits are retained.
    This avoids guessing whether arbitrary adjacent Korean words belong together.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    words = corpus_words() if _SPLIT_WORD.search(text) else frozenset()

    def reconnect(match: re.Match) -> str:
        combined = match[1] + match[2]
        if re.search(r"[가-힣]", combined) and combined in words:
            return match[1]
        return match[0]

    while True:
        formatted = _SPLIT_WORD.sub(reconnect, text)
        if formatted == text:
            return formatted
        text = formatted


def excerpt_html(text: str) -> str:
    # Scope wrapping to this excerpt. Escape document text before adding markup.
    # pre-wrap preserves real breaks; keep-all moves Korean words as a unit.
    return (
        '<div class="source-excerpt" lang="ko" '
        'style="white-space: pre-wrap; word-break: keep-all; overflow-wrap: anywhere;">'
        + escape(readable_excerpt(text))
        + '</div>'
    )
