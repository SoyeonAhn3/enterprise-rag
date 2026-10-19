"""Offline validation for versioned evaluation question lists.

References are checked against the PDFs, never supplied to RAG generation.
Structural checks can also audit historical snapshots without today's PDFs.
"""

from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

from config import DOCUMENTS_DIR, MAX_QUESTION_LENGTH
from ingest import extract_pages

SPLITS = ("dev", "final")
CATEGORIES = ("single_document", "multi_document", "unanswerable")
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field in dataset.")
        result[key] = value
    return result


def _constant(value):
    raise ValueError("Non-finite JSON number in dataset.")


def read_dataset(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=_object, parse_constant=_constant)


def question_key(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def _text(value, location):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected nonempty text: {location}.")
    return value


def _identifier(value, location):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValueError(f"Invalid identifier: {location}.")


def validate_questions(questions, *, documents_dir=None):
    """Validate all annotations; optionally check every reference against PDFs.

    Duplicate wording and family leakage are detectable here. Semantic novelty,
    rubric completeness, and whether a question is unanswerable need review.
    """
    if not isinstance(questions, list) or not questions:
        raise ValueError("Dataset must be a nonempty question list.")
    ids, wordings, families, references = set(), set(), {}, []
    for position, q in enumerate(questions):
        location = f"questions[{position}]"
        if not isinstance(q, dict):
            raise ValueError(f"Expected question object: {location}.")
        _identifier(q.get("id"), f"{location}.id")
        qid = q["id"]
        if qid.casefold() in ids:
            raise ValueError(f"Duplicate question ID: {qid}.")
        ids.add(qid.casefold())  # Attempt filenames must also be unique on Windows.
        wording = _text(q.get("question"), f"{qid}.question")
        if len(wording.strip()) > MAX_QUESTION_LENGTH or not question_key(wording):
            raise ValueError(f"Invalid question length/content: {qid}.")
        normalized = question_key(wording)
        if normalized in wordings:
            raise ValueError(f"Duplicate question wording: {qid}.")
        wordings.add(normalized)
        if q.get("split") not in SPLITS or q.get("category") not in CATEGORIES:
            raise ValueError(f"Invalid split/category: {qid}.")
        _identifier(q.get("family"), f"{qid}.family")
        family = q["family"].casefold()
        if family in families and families[family] != q["split"]:
            raise ValueError(f"Question family leaks across splits: {qid}.")
        families[family] = q["split"]
        if "test_type" in q:
            _identifier(q["test_type"], f"{qid}.test_type")
        if type(q.get("answerable")) is not bool:
            raise ValueError(f"answerable must be boolean: {qid}.")
        if (q["category"] == "unanswerable") != (not q["answerable"]):
            raise ValueError(f"Category and answerability disagree: {qid}.")
        _text(q.get("expected_answer"), f"{qid}.expected_answer")
        criteria = q.get("grading_criteria")
        if not isinstance(criteria, list) or not criteria:
            raise ValueError(f"Missing grading criteria: {qid}.")
        for criterion in criteria:
            _text(criterion, f"{qid}.grading_criteria")
        if len({c.strip() for c in criteria}) != len(criteria):
            raise ValueError(f"Duplicate grading criterion: {qid}.")
        groups = q.get("evidence_groups")
        if not isinstance(groups, list) or bool(groups) != q["answerable"]:
            raise ValueError(f"Missing or inconsistent evidence groups: {qid}.")
        group_ids = set()
        for group in groups:
            if not isinstance(group, dict):
                raise ValueError(f"Invalid evidence group: {qid}.")
            _identifier(group.get("id"), f"{qid}.evidence_groups.id")
            if group["id"] in group_ids:
                raise ValueError(f"Duplicate evidence group: {qid}.")
            group_ids.add(group["id"])
            _text(group.get("claim"), f"{qid}.{group['id']}.claim")
            candidates = group.get("any_of")
            if not isinstance(candidates, list) or not candidates:
                raise ValueError(f"Missing evidence alternatives: {qid}.")
            seen = set()
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    raise ValueError(f"Invalid evidence alternative: {qid}.")
                document = _text(candidate.get("document"), f"{qid}.document")
                if (not document.endswith(".pdf") or any(c in document for c in '/\\:')
                        or document in {".", ".."}):
                    raise ValueError(f"Expected PDF filename: {qid}.")
                page = candidate.get("page")
                if type(page) is not int or page < 1:
                    raise ValueError(f"Expected physical page number starting at 1: {qid}.")
                quote = "".join(_text(candidate.get("quote"), f"{qid}.quote").split())
                key = (document, page, quote)
                if key in seen:
                    raise ValueError(f"Duplicate evidence alternative: {qid}.")
                seen.add(key)
                references.append((qid, group["id"], key))
    if documents_dir is not None:
        pages, _ = extract_pages(Path(documents_dir))
        page_text = {(p.metadata["source_file"], p.metadata["page"]):
                     "".join(p.page_content.split()) for p in pages}
        for qid, group_id, (document, page, quote) in references:
            if quote not in page_text.get((document, page), ""):
                raise ValueError(f"Quote not in PDF: {qid} / {group_id}.")


def reject_overlap(questions, previous):
    """Reject normalized exact duplicates; this is not a semantic novelty test."""
    known = {question_key(q["question"]) for q in previous}
    overlaps = [q["id"] for q in questions if question_key(q["question"]) in known]
    if overlaps:
        raise ValueError("Questions repeat an earlier dataset: " + ", ".join(overlaps))


def select_questions(questions, split):
    if split not in SPLITS:
        raise ValueError("Custom datasets require an explicit --split dev or --split final.")
    selected = [q for q in questions if q["split"] == split]
    if not selected:
        raise ValueError("Selected split is empty.")
    return selected


def dataset_summary(questions, *, configurations=2):
    def counts(items):
        n = len(items)
        return {"questions": n, "answerable": sum(q["answerable"] for q in items),
                "categories": dict(sorted(Counter(q["category"] for q in items).items())),
                "test_types": dict(sorted(Counter(q.get("test_type", q["category"]) for q in items).items())),
                "max_answers": n * configurations, "max_judge_calls": n * configurations,
                "max_total_calls": n * configurations * 2}
    return {"total": counts(questions),
            "splits": {s: counts([q for q in questions if q["split"] == s]) for s in SPLITS},
            "model_calls": 0, "human_review_completed": False,
            "limitation": "Structural and PDF quote checks do not establish semantic correctness or independence."}


def validate_file(path, *, against=(), documents_dir=DOCUMENTS_DIR):
    questions = read_dataset(path)
    validate_questions(questions, documents_dir=documents_dir)
    for previous_path in against:
        previous = read_dataset(previous_path)
        validate_questions(previous)
        reject_overlap(questions, previous)
    return questions
