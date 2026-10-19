"""Freeze/run/verify/report independent grading of saved dev answers.

No answers are generated. Two separately persisted review requests per valid
answer, with no automatic retries. Legacy grades remain untouched.
"""

import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

from config import PROJECT_ROOT
from eval.benchmark import now, read, seal, verify
from eval.evaluate import digest, save_json
from eval.quality import attempt, source_hashes as quality_hashes, run_settings
from eval.split_judge import STAGES, PROMPTS, combine, inputs, response_schema, review, validate
from llm import ClaudeClient


def source_hashes():
    return {**quality_hashes(), **{name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
                                 for name in ("eval/split_judge.py", "eval/review_split.py", "eval/refinement.py")}}


def load_source(source):
    if read(source / "protocol.json").get("kind") == "dev_refinement":
        from eval.refinement import load_completed
    else:
        from eval.quality import load_completed
    protocol, answers = load_completed(source)
    if (protocol.get("dataset_info", {}).get("split") != "dev"
            or not protocol["dataset"] or any(q["split"] != "dev" for q in protocol["dataset"])):
        raise ValueError("Split review requires a completed explicit dev baseline.")
    return protocol, answers


def select(protocol, answers, configurations, question_ids):
    available = {r["configuration"] for r in answers["results"]}
    ids = [q["id"] for q in protocol["dataset"]] if question_ids is None else list(question_ids)
    if (not configurations or len(configurations) != len(set(configurations)) or not set(configurations) <= available
            or not ids or len(ids) != len(set(ids)) or not set(ids) <= {q["id"] for q in protocol["dataset"]}):
        raise ValueError("Select unique existing configurations and dev question IDs.")
    questions = {q["id"]: q for q in protocol["dataset"]}
    rows = {(r["configuration"], r["id"]): r for r in answers["results"]}
    return [(questions[qid], rows[(name, qid)]) for name in configurations for qid in ids]


def item_key(question, row):
    return {"configuration": row["configuration"], "question_id": question["id"],
            "question_sha256": digest(question), "result_sha256": digest(row)}


def execution(items, max_calls):
    required = 2 * sum(r["status"] == "success" for _, r in items)
    if type(max_calls) is not int or max_calls < required:
        raise ValueError(f"Call limit must allow up to {required} independent review requests.")
    return {"max_calls": max_calls, "max_total_calls": required, "new_answers": 0, "automatic_retries": 0}


def freeze(source, output, configurations, question_ids, max_calls):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Freeze requires a new empty output directory.")
    old, answers = load_source(source)
    items = select(old, answers, configurations, question_ids)
    plan = execution(items, max_calls)
    protocol = seal({
        "format_version": 1, "kind": "split_dev_review", "created_at": now(),
        "source_directory": os.path.relpath(source.resolve(), output.resolve()),
        "source_protocol_sha256": old["sha256"], "source_answers_sha256": answers["sha256"],
        "configurations": list(configurations),
        "question_ids": [q["id"] for q in old["dataset"]] if question_ids is None else list(question_ids),
        "items": [item_key(q, r) for q, r in items], "source_sha256": source_hashes(),
        "prompts": PROMPTS, "prompts_sha256": digest(PROMPTS),
        "judge": {"model": run_settings().chat_model, "max_tokens": 4096, "timeout_seconds": 60},
        "execution": plan,
        "scope": "Saved dev answers; independent AI requests, not independent human adjudication or final evaluation.",
    })
    save_json(output / "protocol.json", protocol)
    return protocol


def load_protocol(output, *, current=False):
    protocol = read(output / "protocol.json")
    verify(protocol)
    old, answers = load_source((output / protocol["source_directory"]).resolve())
    items = select(old, answers, protocol["configurations"], protocol["question_ids"])
    if (type(protocol["format_version"]) is not int or protocol["format_version"] != 1
            or protocol["kind"] != "split_dev_review"
            or protocol["source_protocol_sha256"] != old["sha256"]
            or protocol["source_answers_sha256"] != answers["sha256"]
            or protocol["items"] != [item_key(q, r) for q, r in items]
            or protocol["prompts_sha256"] != digest(protocol["prompts"])
            or set(protocol["prompts"]) != set(STAGES)
            or protocol["execution"] != execution(items, protocol["execution"]["max_calls"])):
        raise ValueError("Invalid split-review protocol or changed saved baseline.")
    if current and (protocol["source_sha256"] != source_hashes() or protocol["prompts"] != PROMPTS
                    or protocol["judge"] != {"model": run_settings().chat_model, "max_tokens": 4096, "timeout_seconds": 60}):
        raise ValueError("Frozen code, prompts or judge settings changed; no review was requested.")
    return protocol, items


def audit_attempts(output, protocol, items):
    expected = {f"{stage}_{r['configuration']}_{q['id']}.json": (stage, q, r)
                for q, r in items for stage in STAGES}
    records = []
    for path in sorted((output / "attempts").glob("*")):
        if path.name not in expected:
            raise ValueError("Unknown or temporary review attempt; no request was repeated.")
        stage, question, row = expected[path.name]
        entry = read(path)
        verify(entry)
        if (entry.get("state") != "completed" or entry.get("protocol_sha256") != protocol["sha256"]
                or (entry.get("kind"), entry.get("configuration"), entry.get("question_id"))
                != (stage, row["configuration"], question["id"])):
            raise ValueError("Pending or mismatched review attempt; no request was repeated.")
        record = entry["payload"]
        payload = inputs(question, row)[stage]
        expected_fields = {"stage": stage, "configuration": row["configuration"], "question_id": question["id"],
                           "result_sha256": digest(row), "input": payload, "input_sha256": digest(payload),
                           "prompt_sha256": digest(protocol["prompts"][stage]), "model": protocol["judge"]["model"]}
        if protocol["prompts"][stage].get("response_format") == "keyed_items_v1":
            schema = response_schema(stage, payload, protocol["prompts"][stage])
            expected_fields.update(response_schema=schema, response_schema_sha256=digest(schema))
        if any(record.get(k) != v for k, v in expected_fields.items()):
            raise ValueError("Stage input, identity, prompt or saved-answer linkage changed.")
        if row["status"] != "success":
            if record.get("status") != "not_run" or record.get("reason") != "rag_error":
                raise ValueError("Invalid saved answer must not be graded.")
        elif record.get("status") == "success":
            if record.get("decision") != validate(stage, record["raw_response"], payload, prompt=protocol["prompts"][stage]):
                raise ValueError("Stage decision differs from its raw validated response.")
        elif record.get("status") == "error":
            if not isinstance(record.get("error_type"), str) or not record["error_type"]:
                raise ValueError("Missing safe error classification.")
            if "decision" in record:
                raise ValueError("Failed review must not contain an accepted decision.")
            if "raw_response" in record:
                try:
                    validate(stage, record["raw_response"], payload, prompt=protocol["prompts"][stage])
                except (ValueError, TypeError, KeyError):
                    pass
                else:
                    raise ValueError("A valid raw decision was mislabeled as a review failure.")
        else:
            raise ValueError("Invalid stage status.")
        records.append(record)
    return records


def run(output, *, resume=False):
    protocol, items = load_protocol(output, current=True)
    if (output / "reviews.json").exists():
        raise ValueError("Completed review output already exists.")
    existing = audit_attempts(output, protocol, items)
    if existing and not resume:
        raise ValueError("Saved attempts require explicit --resume.")
    if any(r["status"] == "error" for r in existing):
        raise ValueError("A prior failed request is preserved; automatic retry/continuation is disabled.")
    settings = replace(run_settings(), chat_max_tokens=4096, api_timeout_seconds=60)
    settings.require_anthropic_key()
    for question, row in items:
        for stage in STAGES:
            payload = inputs(question, row)[stage]

            def operation():
                identity = {"configuration": row["configuration"], "question_id": question["id"], "result_sha256": digest(row)}
                if row["status"] != "success":
                    schema = response_schema(stage, payload, protocol["prompts"][stage])
                    return {**identity, "stage": stage, "status": "not_run", "reason": "rag_error",
                            "input": payload, "input_sha256": digest(payload),
                            "prompt_sha256": digest(protocol["prompts"][stage]), "model": settings.chat_model,
                            "response_schema": schema, "response_schema_sha256": digest(schema),
                            "token_usage": None, "latency_ms": 0}
                client = ClaudeClient(settings)
                try:
                    return {**identity, **review(client, stage, payload, prompt=protocol["prompts"][stage])}
                finally:
                    client.close()

            record = attempt(output, protocol, stage, row["configuration"], question["id"], operation, resume=resume)
            print(json.dumps({"stage": stage, "configuration": row["configuration"], "id": question["id"], "status": record["status"]}), flush=True)
            if record["status"] == "error":
                raise ValueError("Review failed; saved the attempt and stopped without retrying.")
    records = audit_attempts(output, protocol, items)
    save_json(output / "reviews.json", seal({"protocol_sha256": protocol["sha256"], "completed_at": now(),
                                           "status": "completed", "records": records}))
    return summarize(output)


def load_completed(output):
    protocol, items = load_protocol(output)
    saved = read(output / "reviews.json")
    verify(saved)
    records = audit_attempts(output, protocol, items)
    if (saved["status"] != "completed" or saved["protocol_sha256"] != protocol["sha256"]
            or saved["records"] != records or len(records) != len(items) * 2):
        raise ValueError("Incomplete or changed split-review output.")
    return protocol, items, saved


def summarize(output):
    protocol, items = load_protocol(output)
    records = audit_attempts(output, protocol, items)
    if (output / "reviews.json").exists():
        load_completed(output)
    by_key = {(r["configuration"], r["question_id"], r["stage"]): r for r in records}
    rows = []
    for q, r in items:
        stages = {s: by_key[(r["configuration"], q["id"], s)] for s in STAGES if (r["configuration"], q["id"], s) in by_key}
        rows.append({"configuration": r["configuration"], "question_id": q["id"], "answer_status": r["status"], **combine(stages)})
    summary = seal({"protocol_sha256": protocol["sha256"], "records_sha256": digest(records),
                    "complete": len(records) == len(items) * 2, "rows": rows,
                    "model_calls": sum(r["status"] in ("success", "error") for r in records),
                    "review_errors": sum(r["status"] == "error" for r in records),
                    "unassessed_answers": sum(r["overall_pass"] is None for r in rows)})
    lines = ["# 분리 채점 결과", "", "저장된 개발용 답변의 독립 요청 결과이며 사람 판정·최종 평가·새 답변의 정확도 측정이 아닙니다.",
             "근거성 요청에는 참고 정답·참고 원문·정확성 판정을 전달하지 않았습니다. 같은 모델의 판단 한계는 남습니다.", "",
             "| 설정 | 문항 | 정확성 | 근거성 | 주장별 인용 | 판단 불확실 | 종합 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    mark = lambda v: "미확정" if v is None else "참" if v else "거짓"
    for r in rows:
        lines.append("| " + " | ".join([r["configuration"], r["question_id"], *[mark(r[k]) for k in ("accurate", "grounded", "citation_complete", "uncertain", "overall_pass")]]) + " |")
    lines += ["", f"모델 요청 {summary['model_calls']}회, 채점 오류 {summary['review_errors']}건, 종합 미확정 {summary['unassessed_answers']}건.",
              "원본 점수는 보존했습니다. 채점 방식을 바꾼 점수 차이는 RAG 구현 개선량이 아닙니다.", ""]
    text = "\n".join(lines)
    if (output / "summary.json").exists() and read(output / "summary.json") != summary:
        raise ValueError("Existing summary differs; preserve it for review.")
    if (output / "report.md").exists() and (output / "report.md").read_text(encoding="utf-8") != text:
        raise ValueError("Existing report differs; preserve manual edits.")
    if not (output / "summary.json").exists(): save_json(output / "summary.json", summary)
    if not (output / "report.md").exists(): (output / "report.md").write_text(text, encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "verify", "report"))
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--configuration", action="append")
    parser.add_argument("--question-id", action="append")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            if args.source_dir is None or not args.configuration or args.max_calls is None or args.resume:
                raise ValueError("freeze requires source, configuration(s) and max-calls, without --resume.")
            result = freeze(args.source_dir, args.output_dir, args.configuration, args.question_id, args.max_calls)
            print(json.dumps(result["execution"]), flush=True)
        else:
            if any(v is not None for v in (args.source_dir, args.configuration, args.question_id, args.max_calls)) or (args.resume and args.command != "run"):
                raise ValueError("Selection/limits apply only to freeze; resume only to run.")
            if args.command == "run": run(args.output_dir, resume=args.resume)
            elif args.command == "verify": load_completed(args.output_dir)
            else: summarize(args.output_dir)
        print(json.dumps({"command": args.command, "status": "completed"}), flush=True)
        return 0
    except Exception as exc:
        print("Split review stopped: " + (str(exc) if type(exc) is ValueError else type(exc).__name__), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
