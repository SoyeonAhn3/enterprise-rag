"""Resume AI grading from saved answers, preserving every earlier attempt.

prepare and verify are offline. run makes only judge calls, stops on its first
failure, and never regenerates RAG answers or retries a completed failed call.
After a provider failure, prepare a NEW directory with --carry-from to retain
successful reviews and explicitly plan another attempt at the remaining ones.
"""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

from config import PROJECT_ROOT, load_settings
from eval.ai_review import review_answer
from eval.benchmark import now, read, seal, verify
from eval.evaluate import save_json
from eval.quality import attempt, judge_hash, load_completed, unused, validate_records
from llm import ClaudeClient, ClaudeError

SOURCE_FILES = ("eval/recover_reviews.py", "eval/ai_review.py", "eval/quality.py", "eval/benchmark.py",
                "eval/evaluate.py", "grounding.py", "llm.py", "config.py")


def code_hashes():
    return {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def key(item):
    return item["configuration"], item.get("question_id", item.get("id"))


def pending_reviews(results, reviews):
    grades = {key(review): review for review in reviews}
    return [key(result) for result in results if result["status"] == "success"
            and grades[key(result)]["status"] == "error"]


def prepare(source, output, *, carry_from=None):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Recovery preparation needs a new, empty directory.")
    protocol, original = load_completed(source)
    reviews, carried_hash = original["reviews"], None
    if carry_from is not None:
        _, carried = verify_recovery(carry_from)
        if carried["base_answers_sha256"] != original["sha256"]:
            raise ValueError("Carried reviews belong to a different original run.")
        reviews, carried_hash = carried["reviews"], carried["sha256"]
    targets = pending_reviews(original["results"], reviews)
    if not targets:
        raise ValueError("No failed AI reviews remain on successful saved answers.")
    plan = seal({"created_at": now(), "scope": "AI reviews only; no RAG generation; stop on first failure.",
                 "source_directory": os.path.relpath(source.resolve(), output.resolve()),
                 "base_protocol_sha256": protocol["sha256"], "base_answers_sha256": original["sha256"],
                 "carried_state_sha256": carried_hash, "reviews": reviews, "targets": targets,
                 "judge": protocol["judge"], "judge_prompt_sha256": protocol["judge_prompt_sha256"],
                 "source_sha256": code_hashes(), "automatic_retries": 0})
    save_json(output / "plan.json", plan)
    return plan


def load_plan(output, *, current=False):
    plan = read(output / "plan.json")
    verify(plan)
    protocol, original = load_completed((output / plan["source_directory"]).resolve())
    if (plan["base_protocol_sha256"] != protocol["sha256"] or plan["base_answers_sha256"] != original["sha256"]
            or plan["judge"] != protocol["judge"] or plan["judge_prompt_sha256"] != protocol["judge_prompt_sha256"]):
        raise ValueError("Recovery plan does not match the original run/judge.")
    validate_records(protocol, original["results"], plan["reviews"])
    if plan["targets"] != [list(k) for k in pending_reviews(original["results"], plan["reviews"])]:
        raise ValueError("Recovery targets must be exactly the failed reviews of successful answers.")
    if current and (plan["source_sha256"] != code_hashes() or plan["judge_prompt_sha256"] != judge_hash()):
        raise ValueError("Recovery code or judge prompt changed after preparation.")
    return plan, protocol, original


def saved_attempts(output, plan):
    expected = {f"review_{name}_{qid}.json": (name, qid) for name, qid in plan["targets"]}
    saved = {}
    for path in sorted((output / "attempts").glob("*")):
        if path.name not in expected:
            raise ValueError("Unknown or temporary recovery attempt.")
        item = read(path)
        verify(item)
        identity = expected[path.name]
        if (item.get("state") != "completed" or item.get("protocol_sha256") != plan["sha256"]
                or item.get("kind") != "review" or (item.get("configuration"), item.get("question_id")) != identity
                or key(item["payload"]) != identity):
            raise ValueError("Pending or mismatched recovery attempt; no request was repeated.")
        saved[identity] = item["payload"]
    return saved


def state_from_attempts(output, plan, *, status):
    saved = saved_attempts(output, plan)
    reviews = [saved.get(key(review), review) for review in plan["reviews"]]
    return seal({"status": status, "plan_sha256": plan["sha256"],
                 "base_answers_sha256": plan["base_answers_sha256"], "reviews": reviews,
                 "attempted": len(saved), "successful_recoveries": sum(g["status"] == "success" for g in saved.values()),
                 "remaining": [list(k) for k in (tuple(t) for t in plan["targets"])
                               if saved.get(k, {}).get("status") != "success"]})


def verify_recovery(output):
    plan, protocol, original = load_plan(output)
    state = read(output / "recovery.json")
    verify(state)
    expected = state_from_attempts(output, plan, status=state["status"])
    if state != expected or (state["status"] == "completed" and state["remaining"]):
        raise ValueError("Recovery summary differs from its preserved attempts.")
    validate_records(protocol, original["results"], state["reviews"])
    return plan, state


def failure_category(exc):
    """Allowlisted codes only; never store provider response text or headers."""
    cause = exc.__cause__ or exc.__context__
    status = getattr(cause, "status_code", None)
    body = getattr(cause, "body", None)
    error = body.get("error", body) if isinstance(body, dict) else {}
    message = error.get("message", "") if isinstance(error, dict) else ""
    lowered = str(message).lower()
    if "credit balance" in lowered or "insufficient credit" in lowered:
        code = "insufficient_credit"
    elif status == 429:
        code = "rate_or_usage_limit"
    elif status in (401, 403):
        code = "authentication_or_access"
    elif "timed out" in str(exc):
        code = "timeout"
    else:
        code = "provider_or_response_error"
    return {"code": code, "http_status": status if type(status) is int else None}


class RecoveryClient(ClaudeClient):
    failure = None

    def generate(self, *args, **kwargs):
        self.failure = None
        try:
            return super().generate(*args, **kwargs)
        except ClaudeError as exc:
            self.failure = failure_category(exc)
            raise


def run(output, *, resume=False):
    plan, protocol, original = load_plan(output, current=True)
    saved = saved_attempts(output, plan)
    validate_records(protocol, original["results"], list(saved.values()))
    target = output / "recovery.json"
    if target.exists():
        _, state = verify_recovery(output)
        if not resume or state["status"] == "completed":
            raise ValueError("Existing recovery requires explicit --resume and must be incomplete.")
    elif saved and not resume:
        raise ValueError("Saved recovery attempts require explicit --resume.")
    else:
        unused(target)
    if any(g["status"] != "success" for g in saved.values()):
        raise ValueError("A failed recovery is preserved. Prepare a new directory with --carry-from before another attempt.")
    settings = replace(load_settings(), chat_model=plan["judge"]["model"], chat_max_tokens=plan["judge"]["max_tokens"],
                       api_timeout_seconds=plan["judge"]["timeout_seconds"], langsmith_tracing=False)
    results = {key(result): result for result in original["results"]}
    questions = {q["id"]: q for q in protocol["dataset"]}
    client = RecoveryClient(settings)
    try:
        save_json(target, state_from_attempts(output, plan, status="running"))
        for name, qid in plan["targets"]:
            def operation():
                review = {"configuration": name, **review_answer(client, questions[qid], results[name, qid])}
                if client.failure is not None:
                    review["provider_failure"] = client.failure
                return review
            review = attempt(output, plan, "review", name, qid, operation, resume=resume)
            status = "stopped_on_error" if review["status"] != "success" else "running"
            state = state_from_attempts(output, plan, status=status)
            save_json(target, state)
            print(json.dumps({"configuration": name, "id": qid, "status": review["status"]}), flush=True)
            if status == "stopped_on_error":
                return state
        state = state_from_attempts(output, plan, status="completed")
        save_json(target, state)
        verify_recovery(output)
        return state
    finally:
        client.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "verify"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--carry-from", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            if args.source_dir is None or args.resume:
                raise ValueError("prepare requires --source-dir and does not accept --resume.")
            plan = prepare(args.source_dir, args.output_dir, carry_from=args.carry_from)
            print(json.dumps({"status": "prepared_no_calls", "pending_reviews": len(plan["targets"])}))
        elif args.source_dir or args.carry_from or (args.command != "run" and args.resume):
            raise ValueError("Source/carry options apply to prepare; --resume applies to run.")
        elif args.command == "run":
            state = run(args.output_dir, resume=args.resume)
            return 0 if state["status"] == "completed" else 2
        else:
            _, state = verify_recovery(args.output_dir)
            print(json.dumps({"status": "verified_saved_recovery", "remaining": len(state["remaining"])}))
        return 0
    except Exception as exc:
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        print(f"Review recovery stopped: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
