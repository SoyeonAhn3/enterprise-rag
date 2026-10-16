"""Offline page-selection comparison: one local search per known question, no LLM.

compare --source-dir OLD_QUALITY --output-dir NEW_DIR
verify --output-dir NEW_DIR
Both selectors receive identical candidates; annotations are scored afterwards.
"""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys

from config import DOCUMENTS_DIR, PROJECT_ROOT, pdf_fingerprints
from eval.benchmark import now, read, seal, verify
from eval.check_retrieval import check_evidence
from eval.evaluate import digest, rate, save_json
from eval.quality import load_completed, run_settings
from rag import Retriever
from retrieval_context import PAGE_SELECTION_POLICY, PageContext

SOURCE_FILES = ("eval/selection.py", "retrieval_context.py", "rag.py", "grounding.py", "tracing.py",
                "config.py", "embeddings.py", "index_store.py", "ingest.py", "eval/check_retrieval.py")


def source_hashes():
    return {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def identity(chunks):
    return [(c["source_file"], c["page"], c["chunk_id"], c["text"]) for c in chunks]


def compare_candidates(context, question, ranked, original):
    # Only the raw question and actual retrieved text reach selection.
    before = context.assemble(ranked, max_sources=5, max_chars=6000)
    after = context.assemble(ranked, question=question["question"], max_sources=5, max_chars=6000)
    full_pages, seen = [], set()
    for chunk in ranked:
        key = (chunk["source_file"], chunk["page"])
        if key not in seen:
            full_pages.append({**chunk, "text": context.pages[key]})
            seen.add(key)
    groups = question["evidence_groups"]
    return {
        "id": question["id"], "question": question["question"], "ranked_chunks": ranked,
        "before": before, "after": after,
        "before_evidence": check_evidence(before, groups), "after_evidence": check_evidence(after, groups),
        "candidate_evidence": check_evidence(full_pages, groups),
        "historical_candidates_match": (identity(ranked) == identity(original["ranked_chunks"])
                                         if original.get("ranked_chunks") else None),
        "historical_context_match": identity(before) == identity(original["retrieved_chunks"]),
    }


def summarize(questions, rows):
    by_id = {q["id"]: q for q in questions}
    if len(rows) != len(by_id) or {r["id"] for r in rows} != set(by_id):
        raise ValueError("Comparison requires one row for every question.")
    answerable = [r for r in rows if by_id[r["id"]]["answerable"]]
    multi = [r for r in rows if by_id[r["id"]]["category"] == "multi_document"]
    metrics = {}
    for mode in ("before", "after", "candidate"):
        check = mode + "_evidence"
        groups = [g for row in answerable for g in row[check]["groups"]]
        metrics[mode] = {
            "complete_required_quotes": rate(sum(r[check]["all_groups_quote_covered"] for r in answerable), len(answerable)),
            "evidence_groups": rate(sum(bool(g["quote_sources"]) for g in groups), len(groups)),
            "multi_document_pages": rate(sum(r[check]["all_groups_page_covered"] for r in multi), len(multi)),
        }
        if mode != "candidate":
            lengths = [sum(len(c["text"]) for c in r[mode]) for r in rows]
            metrics[mode].update(mean_context_chars=statistics.mean(lengths), max_context_chars=max(lengths))
    complete = lambda row, mode: row[mode + "_evidence"]["all_groups_quote_covered"]
    return {
        "metrics": metrics,
        "gains": [r["id"] for r in answerable if not complete(r, "before") and complete(r, "after")],
        "regressions": [r["id"] for r in answerable if complete(r, "before") and not complete(r, "after")],
        "changed_contexts": [r["id"] for r in rows if identity(r["before"]) != identity(r["after"])],
        "historical_candidates_checked": sum(r["historical_candidates_match"] is not None for r in rows),
        "historical_candidates_changed": [r["id"] for r in rows if r["historical_candidates_match"] is False],
        "historical_context_changes": [r["id"] for r in rows if not r["historical_context_match"]],
        "model_calls": 0, "answer_accuracy": None,
    }


def historical_failures(original):
    return [{"configuration": r["configuration"], "id": r["id"], "error_type": r["error_type"],
             "error_stage": r.get("error_stage"), "rule": None,
             "diagnostic_status": "unavailable_in_original_record",
             "explanation": "Original rejected response and exact rule were not retained; no regeneration performed."}
            for r in original["results"] if r["status"] == "error" and r.get("error_type") == "AnswerValidationError"]


def compare(source, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new output directory to preserve previous evidence.")
    old_protocol, original = load_completed(source)
    fingerprints = pdf_fingerprints(DOCUMENTS_DIR)
    if fingerprints != old_protocol["documents_sha256"]:
        raise ValueError("Documents differ from the original run.")
    questions = old_protocol["dataset"]
    protocol = seal({
        "created_at": now(), "scope": "All 60 previously inspected questions; offline retrieval only; no answer-accuracy claim.",
        "source_directory": os.path.relpath(source.resolve(), output.resolve()),
        "base_answers_sha256": original["sha256"], "dataset_sha256": digest(questions),
        "documents_sha256": fingerprints, "source_sha256": source_hashes(),
        "before": "vector_rank", "after": PAGE_SELECTION_POLICY,
        "top_k": 5, "candidate_k": 15, "context_max_chars": 6000,
    })
    save_json(output / "protocol.json", protocol)
    originals = {r["id"]: r for r in original["results"] if r["configuration"] == "pages5"}
    report = {"status": "running", "protocol_sha256": protocol["sha256"], "rows": []}
    retriever = None
    try:
        settings = replace(run_settings(), top_k=5, retrieval_mode="pages", context_max_chars=6000)
        retriever = Retriever(settings)
        if retriever.index.manifest["signature"] != old_protocol["configurations"]["pages5"]["index_signature"]:
            raise ValueError("Index differs from the original comparison.")
        for question in questions:
            retrieval = retriever.retrieve(question["question"])
            row = compare_candidates(retriever.page_context, question, retrieval["ranked_chunks"], originals[question["id"]])
            if row["after"] != retrieval["retrieved_chunks"]:
                raise ValueError("Runtime retrieval and evaluated selection disagree.")
            report["rows"].append(row)
            save_json(output / "comparison.json", seal(report))
        report.update(status="completed", summary=summarize(questions, report["rows"]),
                      historical_validation_failures=historical_failures(original), completed_at=now())
    except Exception as exc:
        report.update(status="error", error_type=type(exc).__name__)
        save_json(output / "comparison.json", seal(report))
        raise
    finally:
        if retriever is not None:
            retriever.close()
    save_json(output / "comparison.json", seal(report))
    return report


def verify_saved(output):
    protocol, report = read(output / "protocol.json"), read(output / "comparison.json")
    verify(protocol)
    verify(report)
    _, original = load_completed((output / protocol["source_directory"]).resolve())
    if (report["status"] != "completed" or report["protocol_sha256"] != protocol["sha256"]
            or protocol["base_answers_sha256"] != original["sha256"]
            or protocol["source_sha256"] != source_hashes()
            or protocol["after"] != PAGE_SELECTION_POLICY
            or (protocol["top_k"], protocol["candidate_k"], protocol["context_max_chars"]) != (5, 15, 6000)):
        raise ValueError("Comparison is incomplete or frozen inputs changed.")
    old_protocol, _ = load_completed((output / protocol["source_directory"]).resolve())
    questions = old_protocol["dataset"]
    if protocol["dataset_sha256"] != digest(questions):
        raise ValueError("Dataset changed.")
    context = PageContext(DOCUMENTS_DIR, protocol["documents_sha256"])
    originals = {r["id"]: r for r in original["results"] if r["configuration"] == "pages5"}
    by_id = {q["id"]: q for q in questions}
    for row in report["rows"]:
        if row != compare_candidates(context, by_id[row["id"]], row["ranked_chunks"], originals[row["id"]]):
            raise ValueError("Saved selection or evidence metrics do not reproduce.")
    if (report["summary"] != summarize(questions, report["rows"])
            or report["historical_validation_failures"] != historical_failures(original)):
        raise ValueError("Saved summary or historical failure audit does not reproduce.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compare", "verify"))
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "compare" and args.source_dir is None:
        parser.error("compare requires --source-dir")
    try:
        report = compare(args.source_dir, args.output_dir) if args.command == "compare" else verify_saved(args.output_dir)
        print(json.dumps({"status": report["status"], **report["summary"]}, ensure_ascii=False))
    except Exception as exc:
        print(f"Offline selection comparison failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
