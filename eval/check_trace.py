"""Verify an actual LangSmith run by reading it back, not just accepting a POST.

Requires LANGSMITH_TRACING=true and a server-side LANGSMITH_API_KEY.
Makes one Claude call; does not make the trace public.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys
import time

from config import PROJECT_ROOT, load_settings
from eval.evaluate import save_json
from llm import ClaudeClient
from rag import RAGAssistant, Retriever
from tracing import LangSmithTracer


def verify_remote_trace(tracer: LangSmithTracer, reference: dict, answer: dict) -> dict:
    if reference["status"] != "enabled" or not reference["run_id"]:
        raise ValueError("Trace was not submitted successfully.")
    run = tracer.client.read_run(reference["run_id"], load_child_runs=True)
    children = {child.name: child for child in run.child_runs or []}
    if (run.error or run.end_time is None or not {"retrieval", "generation"} <= set(children)
            or any(children[name].error or children[name].end_time is None for name in ("retrieval", "generation"))
            or run.outputs.get("answer") != answer["answer"]):
        raise ValueError("Remote trace is incomplete or differs from the observed answer.")
    return {"run_id": str(run.id), "url": tracer.client.get_run_url(run=run, project_name=tracer.project),
            "verified_children": ["retrieval", "generation"], "status": "verified_remote"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "trace_check.json")
    args = parser.parse_args(argv)
    client = retriever = tracer = None
    try:
        settings = load_settings()
        tracer = LangSmithTracer(settings)
        if tracer.status != "enabled":
            print("Trace check needs LANGSMITH_TRACING=true and a valid local LANGSMITH_API_KEY.", file=sys.stderr)
            return 2
        client = ClaudeClient(settings)
        retriever = Retriever(settings)
        answer = RAGAssistant(retriever, client, tracer=tracer).answer(
            "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?")
        # Bounded reads accommodate ingestion delay; never repeat generation.
        verified = None
        for attempt in range(3):
            try:
                verified = verify_remote_trace(tracer, answer["trace"], answer)
                break
            except Exception:
                if attempt < 2:
                    time.sleep(1)
        if verified is None:
            print("Trace could not be verified remotely; the answer was not retried.", file=sys.stderr)
            return 1
        save_json(args.output, {"created_at": datetime.now(timezone.utc).isoformat(), **verified})
        print(f"Verified retrieval/generation trace: {verified['url']}")
        return 0
    except Exception as exc:
        print(f"Trace check failed ({type(exc).__name__}); no credentials or provider details were printed.", file=sys.stderr)
        return 1
    finally:
        for resource in (tracer, client, retriever):
            if resource is not None:
                resource.close()


if __name__ == "__main__":
    raise SystemExit(main())
