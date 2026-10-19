"""Compare saved dev page answers with current pages under one frozen judge.

freeze --source-dir OLD_QUALITY --output-dir NEW --max-calls 60
run [--resume] / verify / report --output-dir NEW
Reuses old answers, never old grades. Final questions are intentionally excluded.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys

from config import DOCUMENTS_DIR, PROJECT_ROOT, pdf_fingerprints
from eval.ai_review import JUDGE_SCHEMA, JUDGE_SYSTEM, review_answer
from eval.benchmark import answer_metrics, answer_once, now, read, seal, verify
from eval.check_retrieval import check_evidence
from eval.datasets import read_dataset
from eval.evaluate import digest, public_configuration, save_json
from eval.quality import (attempt, load_completed as load_baseline, read_attempts,
                          run_settings, source_hashes as quality_hashes, unused)
from grounding import SYSTEM_PROMPT, source_map
from llm import ClaudeClient
from rag import RAGAssistant, Retriever
from retrieval_context import PAGE_SELECTION_POLICY, PageContext

OPTIONS = {"retrieval_mode": "pages", "top_k": 5, "context_max_chars": 6000}
CONFIGS = {"before": OPTIONS, "after": OPTIONS}
SCOPE = "Observed dev cases; saved baseline and new answers graded by the same revised AI judge. No human or final evaluation."


def source_hashes():
    return {**quality_hashes(), "eval/refinement.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def execution_plan(count, eligible_before, max_calls):
    required = 2 * count + eligible_before
    if type(max_calls) is not int or max_calls < required:
        raise ValueError(f"Call limit must allow up to {required} model calls.")
    return {"max_answers": count, "max_judge_calls": count + eligible_before,
            "max_total_calls": required, "max_calls": max_calls,
            "reused_answers": count, "automatic_retries": 0, "judge_workers": 2}


def baseline_rows(report):
    return [{**r, "configuration": "before"} for r in report["results"] if r["configuration"] == "pages5"]


def freeze(source, output, max_calls):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Choose a new empty output directory.")
    old_protocol, old = load_baseline(source)
    questions = old_protocol["dataset"]
    if (old_protocol["format_version"] != 2 or old_protocol["dataset_info"]["split"] != "dev"
            or not questions or any(q["split"] != "dev" for q in questions)):
        raise ValueError("Refinement requires an explicit dev-only baseline.")
    before = baseline_rows(old)
    if len(before) != len(questions) or any(not r.get("ranked_chunks") for r in before):
        raise ValueError("Every baseline page answer needs saved retrieval candidates.")
    execution = execution_plan(len(questions), sum(r["status"] == "success" for r in before), max_calls)
    settings = replace(run_settings(), **OPTIONS)
    with ExitStack() as stack:
        retriever = Retriever(settings)
        stack.callback(retriever.close)
        configuration = public_configuration(settings, retriever.index.manifest)
        if (configuration["index_signature"] != old_protocol["configurations"]["pages5"]["index_signature"]
                or pdf_fingerprints(DOCUMENTS_DIR) != old_protocol["documents_sha256"]):
            raise ValueError("The corpus/index must match the baseline.")
        by_id = {r["id"]: r for r in before}
        replay = []
        for question in questions:
            row = by_id[question["id"]]
            context = retriever.page_context.assemble(row["ranked_chunks"], question=question["question"],
                                                      max_sources=5, max_chars=6000)
            replay.append({"id": question["id"], "sources": context,
                           "evidence_check": check_evidence(context, question["evidence_groups"])})
    protocol = seal({"format_version": 1, "kind": "dev_refinement", "created_at": now(), "scope": SCOPE,
                     "source_directory": os.path.relpath(source.resolve(), output.resolve()),
                     "baseline_protocol_sha256": old_protocol["sha256"], "baseline_answers_sha256": old["sha256"],
                     "dataset": questions, "dataset_info": old_protocol["dataset_info"],
                     "documents_sha256": old_protocol["documents_sha256"], "source_sha256": source_hashes(),
                     "runtime_configuration": configuration, "config_overrides": CONFIGS,
                     "answer_prompt_sha256": digest(SYSTEM_PROMPT), "selection_policy": PAGE_SELECTION_POLICY,
                     "judge_prompt": {"system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA},
                     "judge_prompt_sha256": digest({"system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA}),
                     "judge": {"model": settings.chat_model, "max_tokens": 4096, "timeout_seconds": 60},
                     "execution": execution, "selection_replay": replay})
    save_json(output / "protocol.json", protocol)
    return protocol


def load_protocol(output, *, current=False):
    protocol = read(output / "protocol.json")
    verify(protocol)
    old_protocol, old = load_baseline((output / protocol["source_directory"]).resolve())
    before = baseline_rows(old)
    if (type(protocol.get("format_version")) is not int or protocol["format_version"] != 1
            or protocol.get("kind") != "dev_refinement"
            or protocol["scope"] != SCOPE or protocol["dataset"] != old_protocol["dataset"]
            or protocol["dataset_info"] != old_protocol["dataset_info"]
            or old_protocol["format_version"] != 2 or old_protocol["dataset_info"]["split"] != "dev"
            or any(q["split"] != "dev" for q in protocol["dataset"])
            or protocol["baseline_protocol_sha256"] != old_protocol["sha256"]
            or protocol["baseline_answers_sha256"] != old["sha256"]
            or protocol["config_overrides"] != CONFIGS
            or protocol["documents_sha256"] != old_protocol["documents_sha256"]
            or digest(protocol["judge_prompt"]) != protocol["judge_prompt_sha256"]
            or protocol["execution"] != execution_plan(len(before), sum(r["status"] == "success" for r in before),
                                                       protocol["execution"]["max_calls"])):
        raise ValueError("Invalid refinement protocol or changed baseline.")
    validate_replay(protocol, before)
    if current:
        if (protocol["source_sha256"] != source_hashes()
                or protocol["answer_prompt_sha256"] != digest(SYSTEM_PROMPT)
                or protocol["judge_prompt_sha256"] != digest({"system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA})
                or protocol["judge"] != {"model": run_settings().chat_model, "max_tokens": 4096, "timeout_seconds": 60}
                or protocol["documents_sha256"] != pdf_fingerprints(DOCUMENTS_DIR)
                or digest(read_dataset(PROJECT_ROOT / protocol["dataset_info"]["path"])) != protocol["dataset_info"]["sha256"]):
            raise ValueError("Current code, prompts, PDFs or source dataset differ from the frozen protocol.")
    return protocol, before


def validate_replay(protocol, before):
    """Audit saved selection text/provenance/metrics without rerunning selection."""
    questions = {q["id"]: q for q in protocol["dataset"]}
    rows = protocol["selection_replay"]
    if len(rows) != len(questions) or {r["id"] for r in rows} != set(questions):
        raise ValueError("Selection replay must cover every dev question once.")
    originals = {r["id"]: r for r in before}
    context = PageContext(DOCUMENTS_DIR, protocol["documents_sha256"])
    for row in rows:
        sources = row["sources"]
        source_map(sources, max_sources=5)
        if (sum(len(c["text"]) for c in sources) > 6000
                or len({(c["source_file"], c["page"]) for c in sources}) != len(sources)
                or row["evidence_check"] != check_evidence(sources, questions[row["id"]]["evidence_groups"])):
            raise ValueError("Selection replay budget/pages/metrics mismatch.")
        ranked = originals[row["id"]]["ranked_chunks"]
        for source in sources:
            rank = source["seed_rank"]
            if type(rank) is not int or not 1 <= rank <= len(ranked):
                raise ValueError("Invalid selection seed rank.")
            seed = ranked[rank - 1]
            key = (source["source_file"], source["page"])
            page = context.pages.get(key)
            if (key != (seed["source_file"], seed["page"]) or source["seed_chunk_id"] != seed["chunk_id"]
                    or page is None or source["text"] not in (page, seed["text"])):
                raise ValueError("Selection replay source differs from PDF/seed.")


def run(output, *, resume=False):
    protocol, before = load_protocol(output, current=True)
    unused(output / "answers.json")
    existing, reviews = read_attempts(output, protocol, configurations=CONFIGS)
    if (existing or reviews) and not resume:
        raise ValueError("Saved attempts require explicit --resume.")
    settings = replace(run_settings(), **OPTIONS)
    if not settings.anthropic_api_key.strip():
        raise ValueError("ANTHROPIC_API_KEY is required for this explicit live comparison.")
    with ExitStack() as stack:
        retriever = Retriever(settings)
        stack.callback(retriever.close)
        if public_configuration(settings, retriever.index.manifest) != protocol["runtime_configuration"]:
            raise ValueError("Runtime configuration/index differs from the frozen protocol.")
        client = ClaudeClient(settings)
        stack.callback(client.close)
        assistant = RAGAssistant(retriever, client)
        results = []
        old_by_id = {r["id"]: r for r in before}
        for question in protocol["dataset"]:
            qid = question["id"]
            results.append(attempt(output, protocol, "answer", "before", qid,
                                   lambda: old_by_id[qid], resume=resume))
            result = attempt(output, protocol, "answer", "after", qid,
                             lambda: {"configuration": "after", "split": question["split"],
                                      **answer_once(assistant, question)}, resume=resume)
            results.append(result)
            print(json.dumps({"stage": "answer", "id": qid, "status": result["status"]}), flush=True)

        questions = {q["id"]: q for q in protocol["dataset"]}

        def grade(result):
            def operation():
                judge = ClaudeClient(replace(settings, chat_max_tokens=4096, api_timeout_seconds=60))
                try:
                    return {"configuration": result["configuration"],
                            **review_answer(judge, questions[result["id"]], result)}
                finally:
                    judge.close()
            return attempt(output, protocol, "review", result["configuration"], result["id"], operation, resume=resume)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(grade, result) for result in results]
            for future in as_completed(futures):
                review = future.result()
                print(json.dumps({"stage": "judge", "configuration": review["configuration"],
                                  "id": review["question_id"], "status": review["status"],
                                  "correct": review.get("correct")}), flush=True)
    results, reviews = read_attempts(output, protocol, configurations=CONFIGS)
    save_json(output / "answers.json", seal({"status": "completed", "completed_at": now(),
              "protocol_sha256": protocol["sha256"], "results": results, "reviews": reviews}))
    return summarize(output)


def load_completed(output):
    protocol, before = load_protocol(output)
    report = read(output / "answers.json")
    verify(report)
    results, reviews = read_attempts(output, protocol, configurations=CONFIGS)
    n = len(protocol["dataset"]) * 2
    if (report["status"] != "completed" or report["protocol_sha256"] != protocol["sha256"]
            or len(results) != n or len(reviews) != n or report["results"] != results or report["reviews"] != reviews
            or sorted((r for r in results if r["configuration"] == "before"), key=lambda r: r["id"])
            != sorted(before, key=lambda r: r["id"])):
        raise ValueError("Completed comparison differs from attempts or the saved baseline.")
    return protocol, report


def analyze(protocol, report):
    metrics, assessment, outcomes = {}, {}, {}
    for name in CONFIGS:
        rows = [r for r in report["results"] if r["configuration"] == name]
        grades = [g for g in report["reviews"] if g["configuration"] == name]
        metrics[name] = answer_metrics(protocol["dataset"], rows, grades)
        by_grade = {g["question_id"]: g for g in grades}
        outcomes[name] = {r["id"]: (False if r["status"] == "error" else
                                   by_grade[r["id"]].get("correct") if by_grade[r["id"]]["status"] == "success" else None)
                          for r in rows}
        errors = [g["question_id"] for g in grades if g["status"] == "error"]
        assessment[name] = {"completed_reviews": sum(g["status"] == "success" for g in grades),
                            "eligible_answers": sum(r["status"] == "success" for r in rows),
                            "judge_errors": errors, "fully_assessed": all(v is not None for v in outcomes[name].values()),
                            "validation_errors": [r["id"] for r in rows if r.get("error_stage") == "validation"]}
        assessment[name]["end_to_end_ai_correctness"] = metrics[name]["ai_correctness"] if assessment[name]["fully_assessed"] else None
    common = [qid for qid in outcomes["before"] if all(outcomes[c][qid] is not None for c in CONFIGS)]
    return {"metrics": metrics, "assessment": assessment,
            "paired": {"assessed_outcomes": len(common),
                       "gains": [q for q in common if not outcomes["before"][q] and outcomes["after"][q]],
                       "regressions": [q for q in common if outcomes["before"][q] and not outcomes["after"][q]]},
            "new_answer_attempts": len(protocol["dataset"]),
            "review_calls": sum(g["status"] != "not_run" for g in report["reviews"]),
            "reused_answers": len(protocol["dataset"])}


def report_text(summary):
    m, a = summary["metrics"], summary["assessment"]
    def fraction(value):
        return f"{value['passed']}/{value['total']}" if value else "미확정"
    lines = ["# 개발용 개선 전후 평가", "", "이전 페이지 답변과 새 페이지 답변을 같은 새 AI 채점 기준으로 비교했다.",
             "이전 원본 점수는 변경하지 않았다. 개발용 단일 실행이며 사람 검토·최종 평가가 아니다.", "",
             "| 지표 | 이전 답변 재채점 | 개선 후 답변 |", "| --- | ---: | ---: |"]
    for title, values in [
        ("전체 실행 AI 통과", [fraction(a[c]["end_to_end_ai_correctness"]) for c in CONFIGS]),
        ("필수 근거 전체 확보", [fraction(m[c]["complete_quote_coverage"]) for c in CONFIGS]),
        ("답변 불가 문항 보류", [fraction(m[c]["abstention_contract"]) for c in CONFIGS]),
        ("출력 검증 통과", [f"{m[c]['successful']}/{m[c]['expected']}" for c in CONFIGS]),
        ("AI 채점 완료 / 유효 응답", [f"{a[c]['completed_reviews']}/{a[c]['eligible_answers']}" for c in CONFIGS]),
        ("채점 오류", [str(len(a[c]["judge_errors"])) for c in CONFIGS]),
        ("성공 응답 평균 지연시간(초)", [f"{m[c]['latency_ms']['successful_mean'] / 1000:.2f}" if m[c]['latency_ms']['successful_mean'] is not None else "없음" for c in CONFIGS]),
    ]:
        lines.append(f"| {title} | {' | '.join(values)} |")
    lines += ["", f"실행 결과 비교 가능: {summary['paired']['assessed_outcomes']}문항(검증 실패는 실패 결과).",
              "개선: " + (", ".join(summary["paired"]["gains"]) or "없음") + ".",
              "악화: " + (", ".join(summary["paired"]["regressions"]) or "없음") + ".", "",
              f"새 답변 시도 {summary['new_answer_attempts']}회, 새 채점 요청 {summary['review_calls']}회. 이전 답변 {summary['reused_answers']}개는 재생성하지 않았다.",
              "지연시간은 서로 다른 시점의 관측이다. 검색 선택과 생성 지시를 함께 바꿔 각 효과를 분리하지 않았다.",
              "새 채점 기준과 원래 기준의 점수를 직접 성능 개선량으로 비교하지 않는다. 미채점이 있으면 정답률을 확정하지 않는다.", ""]
    return "\n".join(lines)


def summarize(output):
    protocol, report = load_completed(output)
    summary = seal({"protocol_sha256": protocol["sha256"], "answers_sha256": report["sha256"],
                    "scope": SCOPE, **analyze(protocol, report)})
    content = report_text(summary)
    if (output / "summary.json").exists() and read(output / "summary.json") != summary:
        raise ValueError("Existing summary differs; preserve it for review.")
    if (output / "report.md").exists() and (output / "report.md").read_text(encoding="utf-8") != content:
        raise ValueError("Existing report differs; preserve manual edits.")
    if not (output / "summary.json").exists():
        save_json(output / "summary.json", summary)
    if not (output / "report.md").exists():
        (output / "report.md").write_text(content, encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "verify", "report"))
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            if args.source_dir is None or args.max_calls is None or args.resume:
                raise ValueError("freeze requires --source-dir and --max-calls, without --resume.")
            protocol = freeze(args.source_dir, args.output_dir, args.max_calls)
            print(json.dumps({"status": "frozen_no_model_calls", "execution": protocol["execution"]}), flush=True)
        else:
            if args.source_dir is not None or args.max_calls is not None or (args.resume and args.command != "run"):
                raise ValueError("Source/limit apply only to freeze; --resume applies only to run.")
            if args.command == "run": run(args.output_dir, resume=args.resume)
            elif args.command == "verify": load_completed(args.output_dir)
            else: summarize(args.output_dir)
        print(json.dumps({"command": args.command, "status": "completed"}), flush=True)
        return 0
    except Exception as exc:
        print("Refinement stopped: " + (str(exc) if type(exc) is ValueError else type(exc).__name__), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
