"""Isolated Phase 6 development search comparison and explicit live smoke run.

compare: local E5 retrieval only, 40 dev questions, no generation or AI grading.
smoke: six known cases, up to six Claude answers plus six separate AI reviews.
Each command refuses to overwrite its output. This is not an unseen evaluation.
"""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import sys
from time import perf_counter

from config import DOCUMENTS_DIR, INDEX_DIR, PROJECT_ROOT, load_settings, pdf_fingerprints
from embeddings import create_embeddings
from eval.ai_review import review_answer
from eval.benchmark import answer_metrics, evidence_metrics
from eval.check_retrieval import check_evidence
from eval.evaluate import digest, public_configuration, save_json
from eval.expanded_cases import validate_dataset
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

CONFIGURATIONS = {
    "chunks3": {"retrieval_mode": "chunks", "top_k": 3, "context_max_chars": 6000},
    "chunks5": {"retrieval_mode": "chunks", "top_k": 5, "context_max_chars": 6000},
    "pages5": {"retrieval_mode": "pages", "top_k": 5, "context_max_chars": 6000},
    "pages7": {"retrieval_mode": "pages", "top_k": 7, "context_max_chars": 6000},
}
SMOKE_IDS = ("q01", "q08", "q31", "q54", "q09", "q10")
SOURCE_FILES = ("config.py", "rag.py", "retrieval_context.py", "grounding.py", "index_store.py",
                "ingest.py", "embeddings.py", "llm.py", "tracing.py", "eval/phase6.py",
                "eval/ai_review.py", "eval/check_retrieval.py", "eval/evaluate.py", "eval/benchmark.py")


def now():
    return datetime.now(timezone.utc).isoformat()


def source_hashes():
    return {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def dataset():
    questions = json.loads((PROJECT_ROOT / "eval/questions_v2.json").read_text(encoding="utf-8"))
    validate_dataset(questions)
    return questions


def save_report(target, report):
    report["sha256"] = digest({k: v for k, v in report.items() if k != "sha256"})
    save_json(target, report)


def load_report(target):
    report = json.loads(target.read_text(encoding="utf-8"))
    if report.get("sha256") != digest({k: v for k, v in report.items() if k != "sha256"}):
        raise ValueError("Phase 6 report content does not match its hash.")
    return report


def new_target(output, name):
    target = output / name
    if target.exists() or target.with_name(target.name + ".tmp").exists():
        raise ValueError("Phase 6 output already exists; choose a new output directory to preserve attempts.")
    output.mkdir(parents=True, exist_ok=True)
    return target


def retrieval_attempt(retriever, question):
    started = perf_counter()
    result = {"id": question["id"], "question": question["question"], "retrieved_chunks": [], "ranked_chunks": []}
    try:
        # Only the question reaches the production retriever.
        result.update(retriever.retrieve(question["question"]), status="success")
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__)
    result["retrieval_latency_ms"] = round((perf_counter() - started) * 1000, 2)
    result["evidence_check"] = check_evidence(result["retrieved_chunks"], question["evidence_groups"])
    return result


def search_metrics(questions, results):
    successful = [r for r in results if r["status"] == "success"]
    successful_ids = {r["id"] for r in successful}
    lengths = [sum(len(c["text"]) for c in r["retrieved_chunks"]) for r in successful]
    return {
        **evidence_metrics(questions, results), "expected": len(questions), "successful": len(successful),
        "failed_or_missing_ids": [q["id"] for q in questions if q["id"] not in successful_ids],
        "mean_context_chars": statistics.mean(lengths) if lengths else None,
        "max_context_chars": max(lengths) if lengths else None,
        "mean_retrieval_ms": statistics.mean(r["retrieval_latency_ms"] for r in successful) if successful else None,
    }


def complete_ids(results):
    return {r["id"] for r in results if r["status"] == "success" and r["evidence_check"]["all_groups_quote_covered"]}


def select_candidate(comparisons):
    """Require no lost complete-evidence cases versus k=5; rank declared metrics."""
    baseline = comparisons["chunks5"]
    if baseline["metrics"]["failed_or_missing_ids"]:
        return None
    covered = complete_ids(baseline["results"])
    eligible = [name for name in ("pages5", "pages7")
                if not comparisons[name]["metrics"]["failed_or_missing_ids"]
                and covered <= complete_ids(comparisons[name]["results"])]
    if not eligible:
        return None
    return min(eligible, key=lambda name: (
        -comparisons[name]["metrics"]["complete_quote_coverage"]["passed"],
        -comparisons[name]["metrics"]["evidence_group_recall"]["passed"],
        comparisons[name]["metrics"]["mean_context_chars"], CONFIGURATIONS[name]["top_k"],
    ))


def compare(output, index_dir=INDEX_DIR):
    target = new_target(output, "retrieval_dev.json")
    all_questions = dataset()
    dev = [q for q in all_questions if q["split"] == "dev"]
    settings = replace(load_settings(), langsmith_tracing=False, embedding_local_files_only=True,
                       chunk_size=800, chunk_overlap=120)
    report = {"schema_version": 1, "created_at": now(), "status": "running",
              "scope": "40 development questions; local retrieval only; no answer-correctness or unseen-test claim.",
              "dataset": dev, "full_dataset_sha256": digest(all_questions), "dataset_sha256": digest(dev),
              "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR), "source_sha256": source_hashes(),
              "protocol": CONFIGURATIONS, "comparisons": {}}
    save_report(target, report)
    try:
        provider = create_embeddings(settings)
        for name, options in CONFIGURATIONS.items():
            configured = replace(settings, **options)
            retriever = Retriever(configured, index_dir=index_dir, embeddings=provider)
            try:
                entry = {"configuration": public_configuration(configured, retriever.index.manifest), "results": []}
                report["comparisons"][name] = entry
                for question in dev:
                    entry["results"].append(retrieval_attempt(retriever, question))
                    save_report(target, report)
                entry["metrics"] = search_metrics(dev, entry["results"])
                baseline_ids = complete_ids(report["comparisons"].get("chunks5", entry)["results"])
                entry["lost_complete_vs_chunks5"] = sorted(baseline_ids - complete_ids(entry["results"]))
                entry["gained_complete_vs_chunks5"] = sorted(complete_ids(entry["results"]) - baseline_ids)
                save_report(target, report)
                print(json.dumps({"configuration": name, **entry["metrics"]}), flush=True)
            finally:
                retriever.close()
        # Compute all paired differences only after the baseline is available.
        baseline_ids = complete_ids(report["comparisons"]["chunks5"]["results"])
        for entry in report["comparisons"].values():
            entry["lost_complete_vs_chunks5"] = sorted(baseline_ids - complete_ids(entry["results"]))
            entry["gained_complete_vs_chunks5"] = sorted(complete_ids(entry["results"]) - baseline_ids)
        report.update(status="completed", completed_at=now(), selected_candidate=select_candidate(report["comparisons"]))
    except Exception as exc:
        report.update(status="error", error_type=type(exc).__name__)
        save_report(target, report)
        raise
    save_report(target, report)
    print(json.dumps({"selected_candidate": report["selected_candidate"], "report": str(target)}), flush=True)
    return report


def smoke(output, index_dir=INDEX_DIR):
    search = load_report(output / "retrieval_dev.json")
    questions = dataset()
    selected = search.get("selected_candidate")
    if search.get("status") != "completed" or selected not in ("pages5", "pages7"):
        raise ValueError("A completed development comparison with an eligible candidate is required.")
    if (search["source_sha256"] != source_hashes() or search["full_dataset_sha256"] != digest(questions)
            or search["documents_sha256"] != pdf_fingerprints(DOCUMENTS_DIR)):
        raise ValueError("Code, dataset, or documents changed after selection; run a new comparison first.")
    target = new_target(output, "smoke.json")
    by_id = {q["id"]: q for q in questions}
    selected_questions = [by_id[qid] for qid in SMOKE_IDS]
    settings = replace(load_settings(), **CONFIGURATIONS[selected], langsmith_tracing=False,
                       embedding_local_files_only=True, chunk_size=800, chunk_overlap=120)
    report = {"schema_version": 1, "created_at": now(), "status": "running", "selection_sha256": search["sha256"],
              "source_sha256": source_hashes(), "selected_candidate": selected, "dataset": selected_questions,
              "scope": "Six known regression cases, including previously inspected q54; not an independent holdout.",
              "reviewer_kind": "ai", "human_review_completed": False, "results": [], "reviews": []}
    save_report(target, report)
    client = judge = retriever = None
    try:
        client = ClaudeClient(settings)
        judge = ClaudeClient(replace(settings, chat_max_tokens=4096, api_timeout_seconds=60))
        retriever = Retriever(settings, index_dir=index_dir)
        report["configuration"] = public_configuration(settings, retriever.index.manifest)
        if report["configuration"]["index_signature"] != search["comparisons"][selected]["configuration"]["index_signature"]:
            raise ValueError("The active index changed after candidate selection.")
        assistant = RAGAssistant(retriever, client)
        for question in selected_questions:
            record = {}
            result = {"id": question["id"], "split": question["split"]}
            try:
                result.update(assistant.answer(question["question"], record=record), status="success")
            except Exception as exc:
                result.update(record, status="error", error_type=type(exc).__name__)
            result["evidence_check"] = check_evidence(result.get("retrieved_chunks", []), question["evidence_groups"])
            report["results"].append(result)
            save_report(target, report)  # Preserve the answer before its separate judge call.
            review = review_answer(judge, question, result)
            report["reviews"].append(review)
            save_report(target, report)
            print(json.dumps({"id": question["id"], "status": result["status"],
                              "answerable": result.get("answerable"), "ai_correct": review.get("correct"),
                              "review_status": review["status"]}), flush=True)
        report.update(status="completed", completed_at=now(),
                      metrics=answer_metrics(selected_questions, report["results"], report["reviews"]))
    except Exception as exc:
        report.update(status="error", error_type=type(exc).__name__)
        save_report(target, report)
        raise
    finally:
        for resource in (client, judge, retriever):
            if resource is not None:
                resource.close()
    save_report(target, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("compare", "smoke"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--index-dir", default=INDEX_DIR, type=Path)
    args = parser.parse_args(argv)
    try:
        report = (compare if args.command == "compare" else smoke)(args.output_dir, args.index_dir)
        if args.command == "compare":
            return 0 if report["selected_candidate"] is not None else 1
        return 0 if (not report["metrics"]["rag_errors"] and not report["metrics"]["judge_errors"]
                     and report["metrics"]["ai_correctness"]["passed"] == len(SMOKE_IDS)) else 1
    except Exception as exc:
        # Never echo raw provider/configuration exceptions or credential values.
        print(f"Phase 6 {args.command} failed ({type(exc).__name__}); inspect the saved report if created.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
