"""Frozen, paired regression evaluation on the 60 already inspected v2 cases.

freeze -> run [--resume] -> verify/report, all with --output-dir.
No prompt tuning, automatic model retries, or overwriting historical attempts.
This compares the complete page-mode change, not page expansion in isolation.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import statistics
import sys

from config import DOCUMENTS_DIR, PROJECT_ROOT, load_settings, pdf_fingerprints
from embeddings import create_embeddings
from eval.ai_review import JUDGE_SCHEMA, JUDGE_SYSTEM, judge_input, review_answer, validate_review
from eval.benchmark import answer_metrics, answer_once, now, read, seal, verify
from eval.check_retrieval import check_evidence
from eval.evaluate import digest, public_configuration, rate, save_json
from eval.expanded_cases import DATASET_PATH, validate_dataset
from eval.phase6 import SOURCE_FILES as PHASE6_SOURCE_FILES
from grounding import SYSTEM_PROMPT, validate_answer
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

CONFIGS = {
    "chunks5": {"retrieval_mode": "chunks", "top_k": 5, "context_max_chars": 6000},
    "pages5": {"retrieval_mode": "pages", "top_k": 5, "context_max_chars": 6000},
}
SOURCE_FILES = (*PHASE6_SOURCE_FILES, "eval/quality.py", "eval/expanded_cases.py", "eval/check_trace.py")
SCOPE = ("Known-case regression; all 60 v2 questions were previously inspected. "
         "Same-model AI grading, no completed human review, no unseen holdout. "
         "Page mode changes both candidate depth and context assembly.")


def source_hashes():
    return {p: hashlib.sha256((PROJECT_ROOT / p).read_bytes()).hexdigest() for p in SOURCE_FILES}


def judge_hash():
    return digest({"system": JUDGE_SYSTEM, "schema": JUDGE_SCHEMA})


def run_settings():
    return replace(load_settings(), chunk_size=800, chunk_overlap=120,
                   embedding_local_files_only=True, langsmith_tracing=False)


def unused(path):
    if path.exists() or path.with_name(path.name + ".tmp").exists():
        raise ValueError(f"Output exists; preserve the previous attempt: {path.name}")


def open_retrievers(settings, stack):
    provider = create_embeddings(settings)
    retrievers, configurations = {}, {}
    for name, options in CONFIGS.items():
        configured = replace(settings, **options)
        retriever = Retriever(configured, embeddings=provider)
        stack.callback(retriever.close)
        retrievers[name] = retriever
        configurations[name] = public_configuration(configured, retriever.index.manifest)
    return retrievers, configurations


def freeze(output):
    target = output / "protocol.json"
    if output.exists() and any(output.iterdir()):
        raise ValueError("Freeze needs a new, empty output directory.")
    questions = read(DATASET_PATH)
    validate_dataset(questions)
    settings = run_settings()
    with ExitStack() as stack:
        _, configurations = open_retrievers(settings, stack)
    protocol = seal({"format_version": 1, "created_at": now(), "scope": SCOPE,
                     "dataset": questions, "dataset_sha256": digest(questions),
                     "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR), "source_sha256": source_hashes(),
                     "config_overrides": CONFIGS, "configurations": configurations,
                     "answer_prompt_sha256": digest(SYSTEM_PROMPT), "judge_prompt_sha256": judge_hash(),
                     "judge": {"model": settings.chat_model, "max_tokens": 4096, "timeout_seconds": 60},
                     "execution": {"max_answers": 120, "max_judge_calls": 120, "judge_workers": 2,
                                   "order": "alternate configuration order per question", "automatic_retries": 0}})
    unused(target)
    save_json(target, protocol)
    return protocol


def load_protocol(output):
    protocol = read(output / "protocol.json")
    verify(protocol)
    if (protocol["format_version"] != 1 or digest(protocol["dataset"]) != protocol["dataset_sha256"]
            or protocol["config_overrides"] != CONFIGS or set(protocol["configurations"]) != set(CONFIGS)):
        raise ValueError("Invalid protocol dataset/configurations.")
    questions = protocol["dataset"]
    if len(questions) != 60 or {q["id"] for q in questions} != {f"q{i:02d}" for i in range(1, 61)}:
        raise ValueError("Expected all 60 frozen questions, without duplicates.")
    return protocol


def check_current_protocol(protocol):
    checks = {"dataset_sha256": digest(read(DATASET_PATH)),
              "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR), "source_sha256": source_hashes(),
              "answer_prompt_sha256": digest(SYSTEM_PROMPT), "judge_prompt_sha256": judge_hash()}
    if any(protocol.get(k) != v for k, v in checks.items()):
        raise ValueError("Code, dataset, documents, or prompts changed after freezing; do not reuse this run.")


def attempt(output, protocol, kind, name, qid, operation, *, resume):
    """Claim before calling. An interrupted pending claim never triggers a retry."""
    path = output / "attempts" / f"{kind}_{name}_{qid}.json"
    if path.with_name(path.name + ".tmp").exists():
        raise ValueError("An ambiguous temporary attempt exists; no request was repeated.")
    expected = {"protocol_sha256": protocol["sha256"], "kind": kind, "configuration": name, "question_id": qid}
    if path.exists():
        item = read(path)
        verify(item)
        if (not resume or any(item.get(k) != v for k, v in expected.items())
                or item.get("state") != "completed"):
            raise ValueError("Attempt is pending, mismatched, or requires explicit --resume; no request was repeated.")
        return item["payload"]
    path.parent.mkdir(parents=True, exist_ok=True)
    item = seal({**expected, "state": "pending", "started_at": now()})
    # Exclusive creation also prevents two processes from making the same call.
    with path.open("x", encoding="utf-8") as handle:
        json.dump(item, handle, ensure_ascii=False, indent=2)
    payload = operation()
    item.update(state="completed", completed_at=now(), payload=payload)
    save_json(path, seal(item))
    return payload


def read_attempts(output, protocol):
    results, reviews = [], []
    expected = {f"{kind}_{name}_{q['id']}.json": (kind, name, q["id"])
                for kind in ("answer", "review") for name in CONFIGS for q in protocol["dataset"]}
    for path in sorted((output / "attempts").glob("*")):
        if path.name not in expected:
            raise ValueError("Unknown or temporary attempt file; inspect it before continuing.")
        kind, name, qid = expected[path.name]
        item = read(path)
        verify(item)
        if (item.get("state") != "completed" or item.get("protocol_sha256") != protocol["sha256"]
                or (item.get("kind"), item.get("configuration"), item.get("question_id")) != (kind, name, qid)):
            raise ValueError("An incomplete or mismatched attempt exists; no request was repeated.")
        payload = item["payload"]
        if payload.get("configuration") != name or payload.get("id" if kind == "answer" else "question_id") != qid:
            raise ValueError("Attempt payload identity mismatch.")
        (results if kind == "answer" else reviews).append(payload)
    validate_records(protocol, results, reviews)
    return results, reviews


def validate_records(protocol, results, reviews):
    """Recompute saved answer/grade links; checksums alone are insufficient."""
    questions = {q["id"]: q for q in protocol["dataset"]}
    by_key, grade_keys = {}, set()
    for result in results:
        key = (result.get("configuration"), result.get("id"))
        if key in by_key or key[0] not in CONFIGS or key[1] not in questions:
            raise ValueError("Duplicate or unknown result.")
        by_key[key] = result
        question = questions[key[1]]
        chunks = result.get("retrieved_chunks", [])
        if (result.get("question") != question["question"] or result.get("split") != question["split"]
                or result.get("evidence_check") != check_evidence(chunks, question["evidence_groups"])):
            raise ValueError("Result question or evidence check mismatch.")
        if result.get("status") == "success":
            raw = json.dumps({k: result[k] for k in ("answerable", "claims")}, ensure_ascii=False)
            checked = validate_answer(raw, chunks, max_sources=CONFIGS[key[0]]["top_k"])
            if any(result.get(k) != v for k, v in checked.items()):
                raise ValueError("Stored answer/citations differ from the validated claims.")
            if (result.get("retrieval_mode") != CONFIGS[key[0]]["retrieval_mode"]
                    or result.get("context_chars") != sum(len(c["text"]) for c in chunks)):
                raise ValueError("Result retrieval mode or context size mismatch.")
        elif result.get("status") != "error":
            raise ValueError("Invalid RAG result status.")
    for review in reviews:
        key = (review.get("configuration"), review.get("question_id"))
        if key in grade_keys or key not in by_key:
            raise ValueError("Duplicate review or review without answer.")
        grade_keys.add(key)
        result = by_key[key]
        inputs = judge_input(questions[key[1]], result)
        if (review.get("result_sha256") != digest(result) or review.get("input") != inputs
                or review.get("input_sha256") != digest(inputs) or review.get("reviewer_kind") != "ai"
                or review.get("judge_prompt_sha256") != protocol["judge_prompt_sha256"]
                or review.get("judge_model") != protocol["judge"]["model"]):
            raise ValueError("Review is attached to different answers, criteria, or judge settings.")
        if result["status"] != "success":
            if review.get("status") != "not_run":
                raise ValueError("A failed answer must not receive a grade.")
        elif review.get("status") == "success":
            checked = validate_review(review["raw_response"], inputs)
            if any(review.get(k) != v for k, v in checked.items()):
                raise ValueError("Saved grade differs from the raw judge response.")
        elif review.get("status") != "error":
            raise ValueError("Invalid judge status.")


def run(output, *, resume=False):
    protocol = load_protocol(output)
    unused(output / "answers.json")
    check_current_protocol(protocol)
    existing, existing_reviews = read_attempts(output, protocol)
    if (existing or existing_reviews) and not resume:
        raise ValueError("Saved attempts require explicit --resume.")
    settings = run_settings()
    if not settings.anthropic_api_key.strip():
        raise ValueError("ANTHROPIC_API_KEY is required for this explicit live evaluation.")
    with ExitStack() as stack:
        retrievers, configurations = open_retrievers(settings, stack)
        if configurations != protocol["configurations"]:
            raise ValueError("Runtime configuration/index differs from the frozen protocol.")
        assistants = {}
        for name, options in CONFIGS.items():
            client = ClaudeClient(replace(settings, **options))
            stack.callback(client.close)
            assistants[name] = RAGAssistant(retrievers[name], client)
        results = []
        for position, question in enumerate(protocol["dataset"]):
            order = list(CONFIGS) if position % 2 == 0 else list(reversed(CONFIGS))
            for name in order:
                result = attempt(output, protocol, "answer", name, question["id"],
                                 lambda: {"configuration": name, "split": question["split"],
                                          **answer_once(assistants[name], question)}, resume=resume)
                results.append(result)
                print(json.dumps({"stage": "answer", "configuration": name, "id": question["id"],
                                  "status": result["status"]}), flush=True)
        questions = {q["id"]: q for q in protocol["dataset"]}

        def grade(result):
            def operation():
                judge = ClaudeClient(replace(settings, chat_max_tokens=protocol["judge"]["max_tokens"],
                                            api_timeout_seconds=protocol["judge"]["timeout_seconds"]))
                try:
                    return {"configuration": result["configuration"],
                            **review_answer(judge, questions[result["id"]], result)}
                finally:
                    judge.close()
            return attempt(output, protocol, "review", result["configuration"], result["id"], operation, resume=resume)

        with ThreadPoolExecutor(max_workers=protocol["execution"]["judge_workers"]) as pool:
            futures = [pool.submit(grade, result) for result in results]
            for future in as_completed(futures):
                review = future.result()
                print(json.dumps({"stage": "judge", "configuration": review["configuration"],
                                  "id": review["question_id"], "status": review["status"],
                                  "correct": review.get("correct")}), flush=True)
    results, reviews = read_attempts(output, protocol)
    report = seal({"status": "completed", "completed_at": now(), "protocol_sha256": protocol["sha256"],
                   "results": results, "reviews": reviews})
    save_json(output / "answers.json", report)
    return summarize(output)


def load_completed(output):
    protocol, report = load_protocol(output), read(output / "answers.json")
    verify(report)
    if report.get("status") != "completed" or report.get("protocol_sha256") != protocol["sha256"]:
        raise ValueError("Incomplete run or protocol mismatch.")
    results, reviews = read_attempts(output, protocol)
    if (len(results) != 120 or len(reviews) != 120
            or report["results"] != results or report["reviews"] != reviews):
        raise ValueError("Completed report differs from the 120 answer/review attempts.")
    return protocol, report


def analyze(questions, results, reviews):
    metrics, diagnostics, assessed = {}, {}, {}
    for name in CONFIGS:
        subset = [r for r in results if r["configuration"] == name]
        grades = [r for r in reviews if r["configuration"] == name]
        metrics[name] = answer_metrics(questions, subset, grades)
        by_id, by_grade = {r["id"]: r for r in subset}, {r["question_id"]: r for r in grades}
        lengths = [sum(len(c["text"]) for c in r["retrieved_chunks"]) for r in subset]
        metrics[name]["mean_context_chars"] = statistics.mean(lengths) if lengths else None
        criteria = [c for g in grades if g["status"] == "success" for c in g["criterion_results"]]
        metrics[name]["ai_criteria_satisfied"] = rate(sum(c["satisfied"] for c in criteria),
                                                     sum(len(q["grading_criteria"]) for q in questions))
        diagnostics[name], assessed[name] = [], {}
        for q in questions:
            result, grade = by_id.get(q["id"], {}), by_grade.get(q["id"], {})
            flags = []
            complete = check_evidence(result.get("retrieved_chunks", []), q["evidence_groups"])["all_groups_quote_covered"]
            if q["answerable"] and not complete: flags.append("reference_quote_missing")
            if result.get("status") != "success": flags.append("rag_error_or_missing")
            elif grade.get("status") != "success": flags.append("judge_error_or_missing")
            else:
                assessed[name][q["id"]] = grade["correct"]
                if grade["rubric_uncertain"]: flags.append("ai_rubric_uncertain")
                if not grade["correct"]:
                    flags.append("ai_incorrect_with_complete_evidence" if complete else "ai_incorrect")
                if not grade["grounded"]: flags.append("ai_unsupported_answer")
            if q["answerable"] and result.get("answerable") is False: flags.append("answerable_abstention")
            if flags:
                diagnostics[name].append({"id": q["id"], "flags": flags,
                                          "failed_criteria": [c["id"] for c in grade.get("criterion_results", []) if not c["satisfied"]],
                                          "issues": grade.get("issues", [])})
    before, after = assessed["chunks5"], assessed["pages5"]
    common = set(before) & set(after)
    return {"scope": SCOPE, "metrics": metrics, "diagnostics": diagnostics,
            "paired": {"assessed": len(common),
                       "gains": sorted(q for q in common if not before[q] and after[q]),
                       "regressions": sorted(q for q in common if before[q] and not after[q]),
                       "unassessed": sorted(q["id"] for q in questions if q["id"] not in common)}}


def report_text(summary):
    lines = ["# Phase 6: 기존 60문항 품질 회귀 평가", "",
             "이미 확인한 60문항으로 개선 효과를 점검했다. 새로운 문제에 대한 일반 정확도는 아니다.",
             "답변과 별도 AI 채점은 같은 모델을 사용했다. 사람의 판정은 아직 완료하지 않았다.",
             "두 설정은 동일한 PDF·인덱스·모델·답변 프롬프트를 사용한다. pages는 후보 검색 수와 문맥 구성 방식을 함께 바꾼다.", "",
             "| 지표 | chunks/5 | pages/5 |", "|---|---:|---:|"]
    for label, key in (("AI 기준 통과", "ai_correctness"), ("답변 가능 질문 AI 통과", "ai_answerable_correctness"),
                       ("필수 근거 인용문 전부 포함", "complete_quote_coverage"),
                       ("근거 그룹 회수", "evidence_group_recall"), ("모르는 질문 답변 보류", "abstention_contract"),
                       ("세부 채점 기준 충족", "ai_criteria_satisfied")):
        values = [summary["metrics"][n][key] for n in CONFIGS]
        lines.append("| " + label + " | " + " | ".join(f"{v['passed']}/{v['total']}" for v in values) + " |")
    for label, key in (("평균 문맥 글자 수", "mean_context_chars"),):
        lines.append(f"| {label} | " + " | ".join(f"{summary['metrics'][n][key]:.1f}" for n in CONFIGS) + " |")
    lines.append("| 평균 답변 시간(초) | " + " | ".join(
        f"{summary['metrics'][n]['latency_ms']['successful_mean'] / 1000:.2f}"
        if summary['metrics'][n]['latency_ms']['successful_mean'] is not None else "측정 없음"
        for n in CONFIGS) + " |")
    for label, key in (("생성 입력 토큰(캐시 제외)", "input_tokens"), ("생성 출력 토큰", "output_tokens")):
        lines.append(f"| {label} | " + " | ".join(str(summary["metrics"][n]["generation_tokens"][key]) for n in CONFIGS) + " |")
    paired = summary["paired"]
    lines.extend(["", f"두 방식 모두 AI 채점 가능한 문항: {paired['assessed']}/60.",
                  f"pages에서 통과로 바뀐 문항: {', '.join(paired['gains']) or '없음'}.",
                  f"pages에서 실패로 바뀐 문항: {', '.join(paired['regressions']) or '없음'}.",
                  f"직접 비교할 수 없는 문항: {', '.join(paired['unassessed']) or '없음'}.", "",
                  "## 사람의 확인이 필요한 항목", "",
                  "reference_quote_missing은 정답표의 인용문이 문맥에 전부 없다는 뜻이다. 의미상 답변이 불가능하다는 판정은 아니다.",
                  "ai_incorrect_with_complete_evidence는 근거가 있는데도 AI 기준을 통과하지 못한 경우다. 실제 답변 누락과 채점 문제를 함께 살펴야 한다.", ""])
    for name in CONFIGS:
        lines.append(f"### {name}")
        lines.append("")
        rows = summary["diagnostics"][name]
        lines.extend([f"- {r['id']}: {', '.join(r['flags'])}" for r in rows] or ["- 자동 진단으로 발견된 항목 없음."])
        lines.append("")
    lines.extend(["## 재현과 한계", "", "- protocol.json: 실행 전에 고정한 조건, 원문·코드·질문·프롬프트의 해시.",
                  "- attempts/: 요청 전 pending 기록, 완료 후 원문 답변/AI 채점 기록. 중단된 요청은 자동 재시도하지 않는다.",
                  "- answers.json: 120개 답변 시도와 120개 채점 기록. 오류도 분모에 남긴다.",
                  "- summary.json: 수치, 개선/회귀 문항, AI가 지적한 문장과 근거. 채점 오류를 사람이 수정한 결과는 아니다.",
                  "- 설정별 각 질문에 한 번씩 답했다. 모델·AI 채점의 실행 간 변동이나 통계적 유의성을 측정하지 않았다.",
                  "- verify/report는 API 호출 없이 저장된 인용·채점 원문·기록 연결을 다시 검증한다.",
                  "- 지연시간은 이 로컬 순차 답변 실행의 관찰값이다. 동시 접속/Cloud 성능 시험은 진행하지 않았다.",
                  "- LangSmith 원격 추적 검증은 별도 단건 점검이다. 이 배치 평가에서는 tracing을 끈다.", ""])
    return "\n".join(lines)


def summarize(output):
    protocol, report = load_completed(output)
    summary = seal({"protocol_sha256": protocol["sha256"], "answers_sha256": report["sha256"],
                    **analyze(protocol["dataset"], report["results"], report["reviews"])})
    target = output / "summary.json"
    markdown = output / "report.md"
    content = report_text(summary)
    if target.exists() and read(target) != summary:
        raise ValueError("Summary differs from an existing file; preserve it for review.")
    if markdown.exists() and markdown.read_text(encoding="utf-8") != content:
        raise ValueError("Report differs from an existing file; preserve manual edits.")
    if not target.exists():
        unused(target)
        save_json(target, summary)
    if not markdown.exists():
        markdown.write_text(content, encoding="utf-8")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("freeze", "run", "verify", "report"))
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.resume and args.command != "run":
            raise ValueError("--resume applies only to run.")
        if args.command == "freeze": freeze(args.output_dir)
        elif args.command == "run": run(args.output_dir, resume=args.resume)
        elif args.command == "verify": load_completed(args.output_dir)
        else: summarize(args.output_dir)
        print(json.dumps({"command": args.command, "status": "completed"}), flush=True)
        return 0
    except Exception as exc:
        # Provider messages may contain request details. Never echo them.
        message = str(exc) if type(exc) is ValueError else type(exc).__name__
        print(f"Quality evaluation stopped: {message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
