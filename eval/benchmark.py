"""V2: isolated retrieval comparison, paired live answers, AI review and triage.

python -m eval.benchmark search --output-dir eval/results/phase5_v2_20261014
python -m eval.benchmark run --output-dir eval/results/phase5_v2_20261014
python -m eval.benchmark summarize --output-dir eval/results/phase5_v2_20261014
python -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
from time import perf_counter

from config import DOCUMENTS_DIR, PROJECT_ROOT, load_settings, pdf_fingerprints
from embeddings import create_embeddings
from eval.ai_review import JUDGE_SCHEMA, JUDGE_SYSTEM, judge_input, review_answer, validate_review
from eval.check_retrieval import check_evidence
from eval.evaluate import digest, public_configuration, rate, save_json
from eval.expanded_cases import DATASET_PATH, validate_dataset
from grounding import ABSTENTION_MESSAGE
from index_store import build_index
from ingest import prepare_corpus
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

CONFIGS = {
    "A": {"chunk_size": 800, "chunk_overlap": 120, "top_k": 3},
    "B": {"chunk_size": 800, "chunk_overlap": 120, "top_k": 5},
    "C": {"chunk_size": 500, "chunk_overlap": 120, "top_k": 3},
    "D": {"chunk_size": 800, "chunk_overlap": 0, "top_k": 3},
}
SOURCE_FILES = ["config.py", "rag.py", "grounding.py", "llm.py", "embeddings.py", "ingest.py", "index_store.py",
                "tracing.py", "eval/ai_review.py", "eval/benchmark.py", "eval/expanded_cases.py", "eval/check_retrieval.py"]


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def seal(value):
    value["sha256"] = digest({k: v for k, v in value.items() if k != "sha256"})
    return value


def verify(value):
    if value.get("sha256") != digest({k: v for k, v in value.items() if k != "sha256"}):
        raise ValueError("Artifact fingerprint mismatch.")


def source_hashes():
    return {p: hashlib.sha256((PROJECT_ROOT / p).read_bytes()).hexdigest() for p in SOURCE_FILES}


def evidence_metrics(questions, results):
    by_id = {r["id"]: r for r in results}
    answerable = [q for q in questions if q["answerable"]]
    multi = [q for q in questions if q["category"] == "multi_document"]
    hits = complete = covered_groups = total_groups = multi_pages = 0
    for q in answerable:
        check = check_evidence(by_id.get(q["id"], {}).get("retrieved_chunks", []), q["evidence_groups"])
        hits += check["page_hit_at_3"]  # Legacy helper name; consumes the actual complete top-k list.
        complete += check["all_groups_quote_covered"]
        covered_groups += sum(bool(g["quote_sources"]) for g in check["groups"])
        total_groups += len(check["groups"])
        if q["category"] == "multi_document":
            multi_pages += check["all_groups_page_covered"]
    return {"page_hit_at_k": rate(hits, len(answerable)), "complete_quote_coverage": rate(complete, len(answerable)),
            "evidence_group_recall": rate(covered_groups, total_groups), "multi_page_coverage": rate(multi_pages, len(multi))}


def select_alternative(comparisons):
    def key(name):
        m = comparisons[name]["metrics"]
        return (-m["complete_quote_coverage"]["rate"], -m["evidence_group_recall"]["rate"],
                -m["page_hit_at_k"]["rate"], CONFIGS[name]["top_k"], name)
    return sorted((n for n in comparisons if n != "A"), key=key)[0]


def index_folder(output, name):
    return PROJECT_ROOT / "data/eval_indexes" / output.name / name


def token_counts(corpus, questions, settings):
    from tokenizers import Tokenizer
    paths = sorted((settings.embedding_cache_dir / "models--intfloat--multilingual-e5-small").rglob("tokenizer.json"))
    if settings.embedding_model != "intfloat/multilingual-e5-small" or len(paths) != 1:
        raise ValueError("Review the tokenizer path/limit for this embedding model before benchmarking.")
    tokenizer = Tokenizer.from_file(str(paths[0]))
    tokenizer.no_truncation()
    tokenizer.no_padding()
    passage = [len(tokenizer.encode("passage: " + c.page_content).ids) for c in corpus.chunks]
    query = [len(tokenizer.encode("query: " + q["question"]).ids) for q in questions]
    if max(passage + query) > 512:
        raise ValueError("Benchmark input would exceed the E5 512-token limit.")
    return {"passage_max": max(passage), "query_max": max(query), "limit": 512,
            "tokenizer_sha256": hashlib.sha256(paths[0].read_bytes()).hexdigest()}


def run_search(output):
    target = output / "retrieval_dev.json"
    if target.exists():
        raise ValueError("Retrieval report exists; preserve the frozen selection.")
    questions = read(DATASET_PATH)
    validate_dataset(questions)
    dev = [q for q in questions if q["split"] == "dev"]
    settings = replace(load_settings(), langsmith_tracing=False, retrieval_mode="chunks")
    provider = create_embeddings(settings)
    report = {"created_at": now(), "status": "running", "dataset_sha256": digest(questions), "dataset": questions,
              "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR), "source_sha256": source_hashes(),
              "judge_prompt_sha256": digest({"system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA}),
              "scope": "40 development queries per configuration; no final queries and no generation.",
              "comparisons": {}}
    save_json(target, report)
    for name, options in CONFIGS.items():
        configured = replace(settings, **options)
        corpus = prepare_corpus(chunk_size=configured.chunk_size, chunk_overlap=configured.chunk_overlap)
        tokens = token_counts(corpus, dev, configured)
        folder = index_folder(output, name)
        build_index(corpus, folder, DOCUMENTS_DIR, configured, embeddings=provider)
        retriever = Retriever(configured, index_dir=folder, embeddings=provider)
        try:
            results = [{"id": q["id"], **retriever.retrieve(q["question"])} for q in dev]
            report["comparisons"][name] = {"configuration": public_configuration(configured, retriever.index.manifest),
                                            "tokens": tokens, "results": results, "metrics": evidence_metrics(dev, results)}
        finally:
            retriever.close()
        save_json(target, report)
        print(json.dumps({"configuration": name, "metrics": report["comparisons"][name]["metrics"]}), flush=True)
    report.update(status="completed", selected_alternative=select_alternative(report["comparisons"]), selected_at=now())
    save_json(target, seal(report))
    print(json.dumps({"selected_alternative": report["selected_alternative"]}), flush=True)
    return report


def answer_once(assistant, question):
    started = perf_counter()
    record = {}
    try:
        result = {"id": question["id"], "status": "success", **assistant.answer(question["question"], record=record)}
    except Exception as exc:
        result = {"id": question["id"], "status": "error", "question": question["question"],
                  "error_type": type(exc).__name__, "error_stage": record.get("stage", "unknown"),
                  "retrieved_chunks": record.get("retrieved_chunks", []), "token_usage": record.get("token_usage"),
                  "latency_ms": round((perf_counter() - started) * 1000, 2)}
        result.update({key: record[key] for key in (
            "validation_error", "provider_error", "response_metadata", "ranked_chunks", "retrieval_mode", "context_selection",
            "context_chars", "search_k", "retrieval_latency_ms", "generation_latency_ms", "trace",
        ) if key in record})
    result["evidence_check"] = check_evidence(result["retrieved_chunks"], question["evidence_groups"])
    return result


def run_live(output, *, resume=False):
    target = output / "answers.json"
    if target.exists() and not resume:
        raise ValueError("Answer report exists; do not overwrite or silently repeat paid attempts.")
    search, pilot = read(output / "retrieval_dev.json"), read(output / "pilot.json")
    verify(search)
    verify(pilot)
    questions = read(DATASET_PATH)
    validate_dataset(questions)
    changed_sources = [name for name, value in search["source_sha256"].items() if source_hashes().get(name) != value]
    # This explicit recovery permits only the runner's checkpoint/resume repair.
    # Answering, retrieval, dataset and judge prompt code remain frozen.
    permitted_repair = resume and set(changed_sources) <= {"eval/benchmark.py"}
    if (not pilot["passed"] or (changed_sources and not permitted_repair)
            or search["dataset_sha256"] != digest(questions)
            or search["documents_sha256"] != pdf_fingerprints(DOCUMENTS_DIR)
            or pilot["judge_prompt_sha256"] != search["judge_prompt_sha256"]):
        raise ValueError("Protocol changed or judge pilot failed; freeze and validate before running.")
    names = ["A", search["selected_alternative"]]
    settings = replace(load_settings(), langsmith_tracing=False, retrieval_mode="chunks")
    judge_settings = replace(settings, chat_max_tokens=4096, api_timeout_seconds=60)
    provider = create_embeddings(settings)
    provider.embed_query("구매 규정")  # Warm-up excluded from timed queries.
    retrievers, assistants, clients = {}, {}, []
    report = {"created_at": now(), "status": "running", "protocol_sha256": search["sha256"],
              "pilot_sha256": pilot["sha256"], "dataset": questions, "dataset_sha256": digest(questions),
              "configuration_order": names, "configurations": {}, "results": [], "reviews": [],
              "latency_scope": "RAG retrieval/generation/validation only; excludes model/index/client initialization, judge calls and checkpoint writes.",
              "judge": {"model": judge_settings.chat_model, "max_tokens": judge_settings.chat_max_tokens,
                        "timeout_seconds": judge_settings.api_timeout_seconds, "concurrency": 3,
                        "same_model_as_generator": True, "system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA,
                        "prompt_sha256": search["judge_prompt_sha256"]}}
    if resume:
        report = read(target)
        if (report["status"] != "running" or report.get("pending_attempt")
                or report["protocol_sha256"] != search["sha256"] or report["dataset_sha256"] != digest(questions)
                or report["judge"]["prompt_sha256"] != search["judge_prompt_sha256"]):
            raise ValueError("Cannot resume a completed, ambiguous, or incompatible run.")
        report.setdefault("execution_events", []).append({
            "type": "explicit_resume", "at": now(), "changed_sources": changed_sources,
            "source_sha256": source_hashes(),
            "checkpoint_writer_sha256": hashlib.sha256((PROJECT_ROOT / "eval/evaluate.py").read_bytes()).hexdigest(),
            "note": "Preserve completed answers/reviews; recover missing judge records with explicit additional calls."})
        records_dir = output / "judge_records"
        for file in sorted(records_dir.glob("*.json")) if records_dir.exists() else []:
            review = read(file)
            if not any(g["configuration"] == review["configuration"] and g["question_id"] == review["question_id"] for g in report["reviews"]):
                report["reviews"].append(review)
    try:
        for name in names:
            configured = replace(settings, **CONFIGS[name])
            retrievers[name] = Retriever(configured, index_dir=index_folder(output, name), embeddings=provider)
            client = ClaudeClient(configured)
            clients.append(client)
            assistants[name] = RAGAssistant(retrievers[name], client)
            configuration = public_configuration(configured, retrievers[name].index.manifest)
            if resume and configuration != report["configurations"][name]:
                raise ValueError("Model, index or answer settings changed during recovery.")
            report["configurations"][name] = configuration
        save_json(target, report)
        for split in ("dev", "final"):
            subset = [q for q in questions if q["split"] == split]
            for position, q in enumerate(subset):
                for name in names if position % 2 == 0 else names[::-1]:
                    if any(r["configuration"] == name and r["id"] == q["id"] for r in report["results"]):
                        continue
                    # A checkpoint before each attempt makes interruption explicit.
                    report["pending_attempt"] = {"configuration": name, "id": q["id"], "started_at": now()}
                    save_json(target, report)
                    result = {"configuration": name, "split": split, **answer_once(assistants[name], q)}
                    report["results"].append(result)
                    report.pop("pending_attempt")
                    save_json(target, report)
                    print(json.dumps({"stage": "answer", "split": split, "configuration": name,
                                      "id": q["id"], "status": result["status"], "answerable": result.get("answerable")}), flush=True)
            by_id = {q["id"]: q for q in subset}

            def judge(result):
                client = ClaudeClient(judge_settings)
                try:
                    review = {"configuration": result["configuration"], "split": split,
                              **review_answer(client, by_id[result["id"]], result)}
                    # Each worker durably saves its own result before the aggregate checkpoint.
                    save_json(output / "judge_records" / f"{result['configuration']}_{result['id']}.json", review)
                    return review
                finally:
                    client.close()

            with ThreadPoolExecutor(max_workers=3) as pool:
                existing = {(g["configuration"], g["question_id"]) for g in report["reviews"]}
                futures = [pool.submit(judge, r) for r in report["results"] if r["split"] == split
                           and (r["configuration"], r["id"]) not in existing]
                for future in as_completed(futures):
                    review = future.result()
                    report["reviews"].append(review)
                    save_json(target, report)
                    print(json.dumps({"stage": "judge", "split": split, "configuration": review["configuration"],
                                      "id": review["question_id"], "status": review["status"], "correct": review.get("correct")}), flush=True)
        report.update(status="completed", completed_at=now())
        save_json(target, seal(report))
    finally:
        for resource in clients + list(retrievers.values()):
            resource.close()
    return summarize(output)


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


def sum_usage(items):
    return {key: sum((i.get("token_usage") or {}).get(key, 0) for i in items)
            for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")}


def answer_metrics(questions, results, reviews):
    by_id = {r["id"]: r for r in results}
    grades = {r["question_id"]: r for r in reviews}
    if len(by_id) != len(results) or len(grades) != len(reviews):
        raise ValueError("Duplicate results or reviews.")
    question_ids = {q["id"] for q in questions}
    if set(by_id) - question_ids or set(grades) - set(by_id):
        raise ValueError("Unknown results or reviews without answers.")
    for qid, review in grades.items():
        if review["result_sha256"] != digest(by_id[qid]):
            raise ValueError("Review is attached to different answers.")
    successes = [r for r in results if r["status"] == "success"]
    substantive = [r for r in successes if r["answerable"]]
    answered_questions = [q for q in questions if q["answerable"]]
    unanswerable = [q for q in questions if not q["answerable"]]
    def correct(q):
        return (by_id.get(q["id"], {}).get("status") == "success"
                and grades.get(q["id"], {}).get("status") == "success"
                and grades[q["id"]].get("correct") is True)
    latency = [r["latency_ms"] for r in successes]
    return {**evidence_metrics(questions, results), "expected": len(questions), "attempted": len(results),
            "successful": len(successes), "rag_errors": [r["id"] for r in results if r["status"] != "success"],
            "missing": [q["id"] for q in questions if q["id"] not in by_id],
            "judge_errors": [q["id"] for q in questions if grades.get(q["id"], {}).get("status") != "success"],
            "ai_correctness": rate(sum(correct(q) for q in questions), len(questions)),
            "ai_answerable_correctness": rate(sum(correct(q) for q in answered_questions), len(answered_questions)),
            "ai_grounding_substantive": rate(sum(grades.get(r["id"], {}).get("status") == "success" and
                                                  grades[r["id"]].get("grounded") is True for r in substantive), len(substantive)),
            "abstention_contract": rate(sum(by_id.get(q["id"], {}).get("status") == "success" and
                                             by_id[q["id"]].get("answer") == ABSTENTION_MESSAGE and
                                             by_id[q["id"]].get("answerable") is False and
                                             not by_id[q["id"]].get("sources") and not by_id[q["id"]].get("claims")
                                             for q in unanswerable), len(unanswerable)),
            "answerable_abstentions": [q["id"] for q in answered_questions if by_id.get(q["id"], {}).get("status") == "success" and by_id[q["id"]].get("answerable") is False],
            "latency_ms": {"successful_mean": statistics.mean(latency) if latency else None,
                           "p50": statistics.median(latency) if latency else None, "p95": percentile(latency, .95)},
            "generation_tokens": sum_usage(results), "judge_tokens": sum_usage(reviews)}


def load_completed_run(output):
    """Validate saved evidence and its links without credentials or model calls.

    Source hashes describe the historical execution, not today's reporting code.
    Missing answers/reviews are retained as failures in the derived summaries.
    """
    report, search, pilot = [read(output / name) for name in
                             ("answers.json", "retrieval_dev.json", "pilot.json")]
    for artifact in (report, search, pilot):
        verify(artifact)
        if artifact["status"] != "completed":
            raise ValueError("Finalize the run before summarizing or exporting it.")
    if report.get("pending_attempt"):
        raise ValueError("A pending answer attempt must be resolved before exporting.")
    if (report["protocol_sha256"] != search["sha256"]
            or report["pilot_sha256"] != pilot["sha256"] or pilot["passed"] is not True):
        raise ValueError("Selection protocol or judge pilot mismatch.")
    if (digest(report["dataset"]) != report["dataset_sha256"]
            or digest(search["dataset"]) != search["dataset_sha256"]
            or report["dataset_sha256"] != search["dataset_sha256"]):
        raise ValueError("Dataset hash mismatch.")
    questions = report["dataset"]
    validate_dataset(questions)
    if search["documents_sha256"] != pdf_fingerprints(DOCUMENTS_DIR):
        raise ValueError("PDF corpus differs from the recorded evaluation.")
    prompt_hash = digest({"system": report["judge"]["system"], "schema": report["judge"]["schema"]})
    if any(value != prompt_hash for value in (report["judge"]["prompt_sha256"],
                                              search["judge_prompt_sha256"], pilot["judge_prompt_sha256"])):
        raise ValueError("Judge prompt mismatch.")
    dev = [q for q in questions if q["split"] == "dev"]
    dev_questions = {q["id"]: q["question"] for q in dev}
    comparisons = search["comparisons"]
    if set(comparisons) != set(CONFIGS):
        raise ValueError("Incomplete retrieval comparison.")
    for name, comparison in comparisons.items():
        config, results = comparison["configuration"], comparison["results"]
        options = CONFIGS[name]
        if (config["top_k"] != options["top_k"]
                or config["index_signature"]["chunking"] != {
                    "size": options["chunk_size"], "overlap": options["chunk_overlap"]}
                or config["index_signature"]["files"] != search["documents_sha256"]):
            raise ValueError("Retrieval configuration mismatch.")
        if len(results) != len(dev) or {r["id"] for r in results} != {q["id"] for q in dev}:
            raise ValueError("Retrieval selection must use every development question exactly once.")
        if any(r["question"] != dev_questions[r["id"]] for r in results):
            raise ValueError("Retrieval questions differ from the frozen dataset.")
        if any(len(r["retrieved_chunks"]) > config["top_k"] for r in results):
            raise ValueError("Retrieval exceeds the recorded top-k.")
        if comparison["metrics"] != evidence_metrics(dev, results):
            raise ValueError("Retrieval metrics differ from the saved chunks.")
    selected = search["selected_alternative"]
    if selected != select_alternative(comparisons) or report["configuration_order"] != ["A", selected]:
        raise ValueError("Configuration selection mismatch.")
    if (set(report["configurations"]) != {"A", selected}
            or any(config != comparisons[name]["configuration"] for name, config in report["configurations"].items())):
        raise ValueError("Answer configurations differ from the frozen comparison.")
    by_id = {q["id"]: q for q in questions}
    results = {}
    for result in report["results"]:
        key = (result["configuration"], result["id"])
        question = by_id.get(result["id"])
        if (key in results or key[0] not in report["configurations"] or question is None
                or result["split"] != question["split"] or result["question"] != question["question"]
                or result["status"] not in {"success", "error"}):
            raise ValueError("Duplicate, unknown, or mismatched answer record.")
        if (len(result["retrieved_chunks"]) > report["configurations"][key[0]]["top_k"]
                or result["evidence_check"] != check_evidence(result["retrieved_chunks"], question["evidence_groups"])):
            raise ValueError("Answer evidence differs from the saved chunks.")
        results[key] = result
    seen = set()
    for review in report["reviews"]:
        key = (review["configuration"], review["question_id"])
        result = results.get(key)
        if (key in seen or result is None or review["split"] != result["split"]
                or review["status"] not in {"success", "error", "not_run"}):
            raise ValueError("Duplicate, unknown, or mismatched review record.")
        seen.add(key)
        inputs = judge_input(by_id[key[1]], result)
        if (review["result_sha256"] != digest(result) or review["input"] != inputs
                or review["input_sha256"] != digest(inputs) or review["judge_prompt_sha256"] != prompt_hash
                or review["judge_model"] != report["judge"]["model"] or review["reviewer_kind"] != "ai"):
            raise ValueError("Review is attached to different answers, criteria, or judge settings.")
        if review["status"] == "success":
            parsed = validate_review(review["raw_response"], inputs)
            if result["status"] != "success" or any(review.get(k) != v for k, v in parsed.items()):
                raise ValueError("Saved grade differs from the judge response.")
    return report, search


def build_summary(report):
    """Derive metrics and the review queue from the validated run in memory."""
    names = report["configuration_order"]
    metrics = {"report_sha256": report["sha256"], "reviewer_kind": "ai", "human_review_completed": False,
               "selected_alternative": names[1], "splits": {}, "paired": {}}
    queue = []
    for split in ("dev", "final"):
        questions = [q for q in report["dataset"] if q["split"] == split]
        metrics["splits"][split] = {}
        correct_sets = {}
        for name in names:
            results = [r for r in report["results"] if r["split"] == split and r["configuration"] == name]
            reviews = [r for r in report["reviews"] if r["split"] == split and r["configuration"] == name]
            metrics["splits"][split][name] = answer_metrics(questions, results, reviews)
            grades = {r["question_id"]: r for r in reviews}
            successful_ids = {r["id"] for r in results if r["status"] == "success"}
            correct_sets[name] = {r["question_id"] for r in reviews if r.get("correct") is True
                                 and r["status"] == "success" and r["question_id"] in successful_ids}
            passes = []
            by_id = {r["id"]: r for r in results}
            for q in questions:
                r = by_id.get(q["id"], {})
                g = grades.get(q["id"], {})
                reasons = []
                if not r: reasons.append("missing_answer")
                elif r["status"] != "success": reasons.append("rag_error")
                if g.get("status") != "success": reasons.append("judge_error_or_missing")
                elif g.get("disposition") != "pass": reasons.append("ai_" + g["disposition"])
                if r and q["answerable"] and not r["evidence_check"]["all_groups_quote_covered"]:
                    reasons.append("required_reference_not_fully_retrieved")
                entry = {"configuration": name, "split": split, "id": q["id"], "question": q["question"],
                         "answer": r.get("answer"), "reasons": reasons, "issues": g.get("issues", []),
                         "criteria": g.get("criterion_results", []), "references": q["evidence_groups"],
                         "human_status": "pending"}
                if reasons: queue.append(entry)
                else: passes.append(entry)
            # Two reproducibly chosen passes per split/configuration; human work remains deferred.
            for entry in sorted(passes, key=lambda p: digest({"seed": "phase5-v2", "id": p["id"], "configuration": name}))[:2]:
                entry["reasons"] = ["sample_of_ai_passes"]
                queue.append(entry)
        a, b = (correct_sets[n] for n in names)
        metrics["paired"][split] = {"improved_ids": sorted(b - a), "regressed_ids": sorted(a - b),
                                   "both_correct": len(a & b), "both_not_correct": len(questions) - len(a | b)}
    metrics["review_queue"] = {"entries": len(queue), "flagged_entries": sum(e["reasons"] != ["sample_of_ai_passes"] for e in queue),
                               "sampled_passes": sum(e["reasons"] == ["sample_of_ai_passes"] for e in queue),
                               "unique_questions": len({e["id"] for e in queue})}
    return seal(metrics), seal({"report_sha256": report["sha256"], "human_review_completed": False, "items": queue})


def summarize(output):
    report, _ = load_completed_run(output)
    metrics, queue = build_summary(report)
    save_json(output / "metrics.json", metrics)
    save_json(output / "review_queue.json", queue)
    print(json.dumps(metrics, ensure_ascii=False, indent=2), flush=True)
    return metrics


def load_verified_exports(output):
    report, search = load_completed_run(output)
    metrics, queue = [read(output / name) for name in ("metrics.json", "review_queue.json")]
    for artifact in (metrics, queue):
        verify(artifact)
    if (metrics, queue) != build_summary(report):
        raise ValueError("Saved metrics or review queue differ from the run; recompute with summarize.")
    return report, search, metrics, queue


def verify_saved(output):
    report, _, metrics, queue = load_verified_exports(output)
    groups = [group for split in metrics["splits"].values() for group in split.values()]
    result = {"status": "verified_artifacts", "report_sha256": report["sha256"],
              "questions": len(report["dataset"]), "answers": len(report["results"]),
              "reviews": len(report["reviews"]), "selected_alternative": metrics["selected_alternative"],
              "rag_errors": sum(len(g["rag_errors"]) for g in groups),
              "missing_answers": sum(len(g["missing"]) for g in groups),
              "judge_errors_or_missing": sum(len(g["judge_errors"]) for g in groups),
              "review_queue_entries": len(queue["items"]), "human_review_completed": False}
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["search", "run", "summarize", "verify"])
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--resume", action="store_true", help="Explicitly continue an interrupted run; preserve completed attempts.")
    args = parser.parse_args()
    operation = {"search": run_search, "run": run_live, "summarize": summarize, "verify": verify_saved}[args.command]
    if args.resume:
        if args.command != "run":
            parser.error("--resume requires run")
        run_live(args.output_dir.resolve(), resume=True)
    else:
        operation(args.output_dir.resolve())


if __name__ == "__main__":
    main()
