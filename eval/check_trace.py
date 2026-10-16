"""Check local readiness or verify one real trace by remote readback.

--preflight sends no requests. A live check makes at most one Claude call and
preserves existing output. Cloud Secrets are separate from local configuration.
"""

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

from config import PROJECT_ROOT, load_settings
from eval.evaluate import digest, public_configuration, save_json
from grounding import SYSTEM_PROMPT, abstention, build_prompt, validate_answer
from llm import ClaudeClient
from rag import RAGAssistant, Retriever
from tracing import LangSmithTracer, generation_inputs, generation_outputs

DEFAULT_QUESTION = "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"


def readiness(settings):
    missing = [name for name, present in (
        ("LANGSMITH_TRACING", settings.langsmith_tracing),
        ("LANGSMITH_API_KEY", bool(settings.langsmith_api_key.strip())),
        ("ANTHROPIC_API_KEY", bool(settings.anthropic_api_key.strip())),
    ) if not present]
    return {"status": "ready" if not missing else "not_configured", "missing_settings": missing,
            "configuration": {"retrieval_mode": settings.retrieval_mode, "top_k": settings.top_k,
                              "context_max_chars": settings.context_max_chars, "chat_model": settings.chat_model},
            "scope": "Local process configuration only; not Cloud Secrets or a connection test."}


def _completed(run):
    return (not run.error and run.start_time is not None and run.end_time is not None
            and run.end_time >= run.start_time)


def verify_remote_trace(tracer: LangSmithTracer, reference: dict, answer: dict) -> dict:
    if reference["status"] != "enabled" or not reference["run_id"]:
        raise ValueError("Trace was not submitted successfully.")
    run = tracer.client.read_run(reference["run_id"], load_child_runs=True)
    children = run.child_runs or []
    by_name = {child.name: child for child in children}
    expected_names = {"retrieval", "generation"} if answer["retrieved_chunks"] else {"retrieval"}
    if (str(run.id) != reference["run_id"] or run.name != "enterprise_rag" or run.run_type != "chain"
            or run.parent_run_id is not None or str(run.trace_id) != str(run.id) or not _completed(run)
            or len(by_name) != len(children) or set(by_name) != expected_names):
        raise ValueError("Remote trace is incomplete or has an invalid hierarchy.")
    if (not isinstance(run.outputs, dict) or run.inputs != {"question": answer["question"]}
            or any(run.outputs.get(k) != answer[k] for k in ("answer", "answerable", "claims", "sources", "token_usage"))):
        raise ValueError("Remote root inputs/output differ from the observed answer.")
    for child in children:
        if (not _completed(child) or str(child.parent_run_id) != str(run.id) or str(child.trace_id) != str(run.id)
                or child.run_type != ("retriever" if child.name == "retrieval" else "llm")):
            raise ValueError("Remote trace child is incomplete or has an invalid parent/type.")
    for item in [run, *children]:
        metadata = (item.extra or {}).get("metadata", {})
        if any(metadata.get(k) != value for k, value in tracer.metadata.items()):
            raise ValueError("Remote configuration differs from the requested settings.")
    retrieval = by_name["retrieval"]
    keys = ("question", "retrieved_chunks", "ranked_chunks", "retrieval_mode", "search_k", "context_chars")
    if (not isinstance(retrieval.outputs, dict) or retrieval.inputs != {"question": answer["question"]}
            or any(retrieval.outputs.get(k) != answer.get(k) for k in keys)):
        raise ValueError("Remote retrieval differs from the actual context.")
    if "generation" in by_name:
        generation = by_name["generation"]
        expected_prompt = build_prompt(answer["question"], answer["retrieved_chunks"], max_sources=tracer.top_k)
        if not isinstance(generation.outputs, dict) or generation.inputs != generation_inputs(SYSTEM_PROMPT, expected_prompt):
            raise ValueError("Remote generation prompt differs from the observed context.")
        raw = generation.outputs.get("text")
        grounded = validate_answer(raw, answer["retrieved_chunks"], max_sources=tracer.top_k)
        expected_output = generation_outputs(raw, answer["token_usage"])
        if (any(generation.outputs.get(k) != v for k, v in expected_output.items())
                or any(answer[k] != v for k, v in grounded.items())):
            raise ValueError("Remote generation output or token usage differs from the answer.")
    elif any(answer[k] != v for k, v in abstention().items()):
        raise ValueError("An empty-context trace must preserve abstention.")
    return {"run_id": str(run.id), "url": tracer.client.get_run_url(run=run, project_name=tracer.project),
            "verified_children": sorted(expected_names), "status": "verified_remote",
            "verified_fields": ["hierarchy", "settings", "question", "context", "answer"]
                               + (["prompt", "token_usage"] if "generation" in by_name else []),
            "context_sha256": digest(answer["retrieved_chunks"]),
            "answer_sha256": digest({k: answer[k] for k in ("answer", "answerable", "claims", "sources")})}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--retrieval-mode", choices=("chunks", "pages"))
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--context-max-chars", type=int)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args(argv)
    client = retriever = tracer = None
    report = target = None
    try:
        overrides = {name: getattr(args, name) for name in ("retrieval_mode", "top_k", "context_max_chars")
                     if getattr(args, name) is not None}
        settings = replace(load_settings(), **overrides)
        preflight = readiness(settings)
        if args.preflight:
            if args.output:
                if args.output.exists() or args.output.with_name(args.output.name + ".tmp").exists():
                    raise ValueError("Output exists; preserve the previous attempt.")
                save_json(args.output, preflight)
            print(json.dumps(preflight, ensure_ascii=False))
            return 0 if preflight["status"] == "ready" else 2
        if preflight["status"] != "ready":
            print("Trace check needs: " + ", ".join(preflight["missing_settings"]), file=sys.stderr)
            return 2
        target = args.output or PROJECT_ROOT / "data" / "trace_check.json"
        if target.exists() or target.with_name(target.name + ".tmp").exists():
            raise ValueError("Output exists; preserve the previous attempt.")
        tracer = LangSmithTracer(settings)
        if tracer.status != "enabled":
            raise ValueError("Trace client could not be initialized.")
        retriever = Retriever(settings)
        report = {"created_at": datetime.now(timezone.utc).isoformat(), "status": "started",
                  "scope": "Local RAG execution verified against remote LangSmith; not a Cloud app check.",
                  "configuration": public_configuration(settings, retriever.index.manifest)}
        save_json(target, report)
        client = ClaudeClient(settings)
        answer = RAGAssistant(retriever, client, tracer=tracer).answer(args.question)
        report.update(status="answer_recorded", observed=answer)
        save_json(target, report)
        # Bounded reads accommodate ingestion delay; never repeat generation.
        verified = None
        failure_type = None
        for attempt in range(3):
            try:
                verified = verify_remote_trace(tracer, answer["trace"], answer)
                break
            except Exception as exc:
                failure_type = type(exc).__name__
                if attempt < 2:
                    time.sleep(1)
        if verified is None:
            report.update(status="verification_failed", verification_error_type=failure_type)
            save_json(target, report)
            print("Remote trace was not verified; the answer and attempt were preserved without retrying generation.", file=sys.stderr)
            return 1
        report.update(verified)
        save_json(target, report)
        print(f"Verified retrieval/generation trace: {verified['url']}")
        return 0
    except Exception as exc:
        if report is not None:
            report.update(status="error", error_type=type(exc).__name__)
            save_json(target, report)
        print(f"Trace check failed ({type(exc).__name__}); no credentials or provider details were printed.", file=sys.stderr)
        return 1
    finally:
        for resource in (tracer, client, retriever):
            if resource is not None:
                resource.close()


if __name__ == "__main__":
    raise SystemExit(main())
