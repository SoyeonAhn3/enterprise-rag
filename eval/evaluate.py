"""Run the fixed ten-question benchmark or recompute metrics without API calls.

python -m eval.evaluate                       # ten Claude requests, new report
python -m eval.evaluate --report RUN.json      # offline recomputation
python -m eval.evaluate --report RUN.json --review REVIEW.json
"""

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter, sleep
from uuid import uuid4

from config import DOCUMENTS_DIR, INDEX_DIR, PROJECT_ROOT, Settings, load_settings
from eval.check_retrieval import check_evidence
from grounding import ABSTENTION_MESSAGE
from llm import ClaudeClient
from rag import RAGAssistant, Retriever
from tracing import LangSmithTracer

RESULTS_DIR = PROJECT_ROOT / "eval" / "results"


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def save_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Windows readers and sync clients can briefly deny atomic replacement.
    # Retry only this file operation, never the model request that produced it.
    for attempt in range(20):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            sleep(min(0.05 * (attempt + 1), 0.25))


def validate_dataset(questions: list[dict]):
    if (not isinstance(questions, list) or len(questions) != 10
            or {item.get("id") for item in questions} != {f"q{i:02d}" for i in range(1, 11)}):
        raise ValueError("The benchmark requires exactly q01 through q10, without duplicate IDs.")
    counts = {"single_document": 0, "multi_document": 0, "unanswerable": 0}
    for item in questions:
        if item.get("category") not in counts or type(item.get("answerable")) is not bool:
            raise ValueError("Invalid benchmark category or answerability.")
        counts[item["category"]] += 1
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise ValueError("Benchmark questions must not be empty.")
        groups = item.get("evidence_groups")
        if not isinstance(groups, list) or bool(groups) != item["answerable"]:
            raise ValueError("Answerable questions need evidence; unanswerable questions must have none.")
        if (item["category"] == "unanswerable") == item["answerable"]:
            raise ValueError("Benchmark category and answerability disagree.")
        if not item.get("grading_criteria"):
            raise ValueError("Benchmark questions need grading criteria.")
        for group in groups:
            if not group.get("any_of"):
                raise ValueError("Each evidence group needs at least one alternative.")
            for candidate in group["any_of"]:
                if (not isinstance(candidate.get("quote"), str) or not candidate["quote"].strip()
                        or type(candidate.get("page")) is not int or candidate["page"] < 1
                        or not candidate.get("document")):
                    raise ValueError("Invalid evidence candidate.")
    if counts != {"single_document": 6, "multi_document": 2, "unanswerable": 2}:
        raise ValueError("Expected six single-document, two multi-document, and two unanswerable questions.")


def rate(passed: int, total: int) -> dict:
    return {"passed": passed, "total": total, "rate": passed / total if total else None}


def report_fingerprint(report: dict) -> str:
    return digest({key: report[key] for key in ("run_id", "dataset_sha256", "configuration", "results")})


def calculate_metrics(report: dict, review: dict | None = None) -> dict:
    questions = report["dataset"]
    validate_dataset(questions)
    if digest(questions) != report["dataset_sha256"]:
        raise ValueError("Saved benchmark annotations do not match their recorded hash.")
    if report.get("report_sha256") and report["report_sha256"] != report_fingerprint(report):
        raise ValueError("Saved results do not match their recorded hash.")
    by_id = {item["id"]: item for item in report["results"]}
    if len(by_id) != len(report["results"]) or set(by_id) - {item["id"] for item in questions}:
        raise ValueError("Results contain duplicate or unknown question IDs.")
    hits = coverage = quotes = abstentions = answerability = 0
    successes, failures, missing = [], [], []
    for question in questions:
        item = by_id.get(question["id"])
        if item is None:
            missing.append(question["id"])
            continue
        evidence = check_evidence(item.get("retrieved_chunks", [])[:3], question["evidence_groups"])
        if question["answerable"]:
            hits += bool(evidence["page_hit_at_3"])
            quotes += bool(evidence["all_groups_quote_covered"])
        if question["category"] == "multi_document":
            coverage += bool(evidence["all_groups_page_covered"])
        if item.get("status") != "success":
            failures.append(question["id"])
            continue
        successes.append(item)
        answerability += item.get("answerable") is question["answerable"]
        if not question["answerable"]:
            abstentions += (item.get("answerable") is False and item.get("answer") == ABSTENTION_MESSAGE
                           and not item.get("sources") and not item.get("claims"))
    successful_times = [item["latency_ms"] for item in successes]
    attempted_times = [item["latency_ms"] for item in report["results"]]
    metrics = {
        "expected": 10, "attempted": len(by_id), "successful": len(successes),
        "failed_ids": failures, "missing_ids": missing,
        "retrieval_hit_at_3": rate(hits, 8), "multi_document_coverage": rate(coverage, 2),
        "all_required_quotes_retrieved": rate(quotes, 8),
        "answerability_agreement": rate(answerability, 10),
        "abstention_contract": rate(abstentions, 2),
        "latency_ms": {
            "all_ten_success_mean": statistics.mean(successful_times) if len(successes) == 10 else None,
            "successful_mean": statistics.mean(successful_times) if successful_times else None,
            "attempted_mean_including_failures": statistics.mean(attempted_times) if attempted_times else None,
            "successful_min": min(successful_times) if successful_times else None,
            "successful_max": max(successful_times) if successful_times else None,
        },
        "review": {"status": "pending", "reviewer_kind": None, "correctness": None, "grounding": None},
    }
    if review is not None:
        if review.get("report_sha256") != report_fingerprint(report):
            raise ValueError("Review belongs to different answers or settings; it cannot grade this report.")
        if review.get("reviewer_kind") not in {"human", "agent"} or not review.get("reviewer"):
            raise ValueError("Review must identify a human or agent reviewer.")
        entries = review.get("items", [])
        reviewed = {item["id"]: item for item in entries}
        if len(reviewed) != len(entries) or set(reviewed) != {item["id"] for item in questions}:
            raise ValueError("Review must include each of the ten questions exactly once.")
        for item in entries:
            if (type(item.get("correct")) is not bool or type(item.get("grounded")) is not bool
                    or not isinstance(item.get("notes"), str) or not item["notes"].strip()):
                raise ValueError("Each review needs boolean decisions and an evidence-based explanation.")
            if by_id.get(item["id"], {}).get("status") != "success" and (item["correct"] or item["grounded"]):
                raise ValueError("A missing or failed answer cannot be graded as correct or grounded.")
        metrics["review"] = {
            "status": "complete", "reviewer_kind": review["reviewer_kind"], "reviewer": review["reviewer"],
            "correctness": rate(sum(item["correct"] for item in entries), 10),
            "grounding": rate(sum(item["grounded"] for item in entries), 10),
        }
    return metrics


def public_configuration(settings: Settings, manifest: dict) -> dict:
    return {
        "provider": "anthropic", "chat_model": settings.chat_model,
        "max_tokens": settings.chat_max_tokens, "timeout_seconds": settings.api_timeout_seconds,
        "top_k": settings.top_k, "embedding": manifest["signature"]["embedding"],
        "retrieval_mode": settings.retrieval_mode, "context_max_chars": settings.context_max_chars,
        "index_signature": manifest["signature"], "index_collection": manifest["collection"],
        "chunk_count": manifest["chunk_count"], "python": platform.python_version(),
        "libraries": {name: version(name) for name in ("anthropic", "fastembed", "chromadb", "langsmith")},
        "source_sha256": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                          for name in ("rag.py", "retrieval_context.py", "grounding.py", "llm.py", "embeddings.py", "index_store.py", "tracing.py")},
        "tracing_requested": settings.langsmith_tracing,
    }


def run_evaluation(assistant: RAGAssistant, questions: list[dict], configuration: dict, *, output: Path) -> dict:
    validate_dataset(questions)
    if output.exists():
        raise ValueError("Evaluation output already exists; choose a new path to preserve the original run.")
    report = {
        "schema_version": 1, "run_id": str(uuid4()), "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "running", "dataset": questions, "dataset_sha256": digest(questions),
        "configuration": configuration, "results": [],
        "latency_scope": "Per question including trace writes; excludes model/index/client initialization.",
    }
    save_json(output, report)
    for question in questions:
        started = perf_counter()
        record = {}
        try:
            answer = assistant.answer(question["question"], record=record)
            result = {"id": question["id"], "status": "success", **answer}
        except Exception as exc:
            result = {
                "id": question["id"], "status": "error", "question": question["question"],
                "error": {"type": type(exc).__name__, "stage": record.get("stage", "unknown"),
                          "message": "Request failed; no successful answer or abstention was recorded."},
                "retrieved_chunks": record.get("retrieved_chunks", []),
                "retrieval_latency_ms": record.get("retrieval_latency_ms"),
                "generation_latency_ms": record.get("generation_latency_ms"),
                "latency_ms": round((perf_counter() - started) * 1000, 2),
                "trace": record.get("trace", {"status": "unavailable", "run_id": None}),
            }
            result.update({key: record[key] for key in (
                "validation_error", "response_metadata", "ranked_chunks", "retrieval_mode", "context_selection",
                "context_chars", "search_k", "token_usage",
            ) if key in record})
        result["evidence_check"] = check_evidence(result["retrieved_chunks"], question["evidence_groups"])
        report["results"].append(result)
        report["metrics"] = calculate_metrics(report)
        save_json(output, report)
        print(json.dumps({"id": question["id"], "status": result["status"],
                          "answerable": result.get("answerable"), "latency_ms": result["latency_ms"]},
                         ensure_ascii=False), flush=True)
    report["status"] = "completed" if not report["metrics"]["failed_ids"] else "completed_with_errors"
    report["completed_at"] = datetime.now(timezone.utc).isoformat()
    report["report_sha256"] = report_fingerprint(report)
    save_json(output, report)
    return report


def review_template(report: dict) -> dict:
    return {
        "report_sha256": report_fingerprint(report), "reviewer_kind": "human", "reviewer": "",
        "items": [{"id": item["id"], "correct": None, "grounded": None, "notes": ""}
                  for item in report["dataset"]],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path, help="Recompute a saved run without API calls.")
    parser.add_argument("--review", type=Path, help="Apply a report-bound review; never infer grades from keywords.")
    parser.add_argument("--review-template", type=Path, help="Write a blank human review for --report.")
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--documents", type=Path, default=DOCUMENTS_DIR)
    args = parser.parse_args(argv)
    if (args.review or args.review_template) and not args.report:
        parser.error("--review and --review-template require --report")
    client = retriever = tracer = None
    try:
        if args.report:
            report = json.loads(args.report.read_text(encoding="utf-8"))
            review = json.loads(args.review.read_text(encoding="utf-8")) if args.review else None
            metrics = calculate_metrics(report, review)
            if args.review_template:
                if args.review_template.exists():
                    raise ValueError("Review template already exists; choose a new path.")
                save_json(args.review_template, review_template(report))
            print(json.dumps(metrics, ensure_ascii=False, indent=2))
            return 0
        settings = load_settings()
        if settings.top_k != 3 or settings.retrieval_mode != "chunks":
            raise ValueError("The historical ten-question evaluator requires k=3 and chunks mode; use eval.phase6 for page-context experiments.")
        questions = json.loads((PROJECT_ROOT / "eval/questions.json").read_text(encoding="utf-8"))
        validate_dataset(questions)
        output = args.output or RESULTS_DIR / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
        client = ClaudeClient(settings)
        retriever = Retriever(settings, index_dir=args.index_dir, documents_dir=args.documents)
        tracer = LangSmithTracer(settings)
        report = run_evaluation(RAGAssistant(retriever, client, tracer=tracer), questions,
                                public_configuration(settings, retriever.index.manifest), output=output)
        print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
        print(f"Saved {output}; answer correctness remains ungraded until a review is supplied.")
        return 0 if report["status"] == "completed" else 1
    except Exception as exc:
        print(f"Evaluation failed ({type(exc).__name__}); check configuration, paths, and dataset.", file=sys.stderr)
        return 1
    finally:
        for resource in (tracer, client, retriever):
            if resource is not None:
                resource.close()


if __name__ == "__main__":
    raise SystemExit(main())
