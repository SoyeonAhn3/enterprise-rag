"""Export verified V2 artifacts to readable Korean Markdown and Excel-friendly CSV."""

import argparse
import csv
import json
from pathlib import Path

from eval.benchmark import load_verified_exports, read, verify


def fraction(value):
    if value["rate"] is None:
        return f"{value['passed']}/{value['total']} (해당 없음)"
    return f"{value['passed']}/{value['total']} ({value['rate']:.1%})"


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def export(output: Path):
    report, search, metrics, queue = load_verified_exports(output)
    review_csv = output / "review_queue.csv"
    if review_csv.exists():
        with review_csv.open(encoding="utf-8-sig", newline="") as handle:
            if any((row.get("human_notes") or "").strip()
                   or (row.get("human_status") or "pending").strip() != "pending"
                   for row in csv.DictReader(handle)):
                raise ValueError("review_queue.csv contains human work; move it to a separate review file before exporting.")
    notes_path = output / "review_notes.json"
    notes = {"items": []}
    if notes_path.exists():
        notes = read(notes_path)
        verify(notes)
        if notes["report_sha256"] != report["sha256"]:
            raise ValueError("Review notes belong to different answers.")
    notes_by_key = {(n["configuration"], n["id"]): n["notes"] for n in notes["items"]}
    grades = {(g["configuration"], g["question_id"]): g for g in report["reviews"]}
    results = list(report["results"])
    recorded = {(r["configuration"], r["id"]) for r in results}
    for name in report["configuration_order"]:
        for question in report["dataset"]:
            if (name, question["id"]) not in recorded:
                results.append({"configuration": name, "id": question["id"], "split": question["split"],
                                "question": question["question"], "status": "missing", "latency_ms": None,
                                "retrieved_chunks": []})
    answer_rows = []
    for result in results:
        grade = grades.get((result["configuration"], result["id"]), {})
        config = report["configurations"][result["configuration"]]
        chunking = config["index_signature"]["chunking"]
        answer_rows.append({"id": result["id"], "split": result["split"], "configuration": result["configuration"],
                     "question": result["question"], "rag_status": result["status"], "answer": result.get("answer", ""),
                     "ai_correct": grade.get("correct", ""), "judge_status": grade.get("status", "missing"),
                     "ai_issues": json.dumps(grade.get("issues", []), ensure_ascii=False),
                     "latency_ms": result["latency_ms"], "model": config["chat_model"],
                     "chunk_size": chunking["size"], "overlap": chunking["overlap"], "top_k": config["top_k"],
                     "retrieved_chunks": json.dumps(result["retrieved_chunks"], ensure_ascii=False),
                     "generation_token_usage": json.dumps(result.get("token_usage"), ensure_ascii=False)})
    queue_rows = [{"configuration": e["configuration"], "split": e["split"], "id": e["id"],
             "question": e["question"], "answer": e["answer"], "reasons": "; ".join(e["reasons"]),
             "issues": json.dumps(e["issues"], ensure_ascii=False), "criteria": json.dumps(e["criteria"], ensure_ascii=False),
             "references": json.dumps(e["references"], ensure_ascii=False), "human_status": e["human_status"],
             "agent_review_note": notes_by_key.get((e["configuration"], e["id"]), ""),
             "human_notes": ""} for e in queue["items"]]
    dev_count = sum(q["split"] == "dev" for q in report["dataset"])
    final_count = sum(q["split"] == "final" for q in report["dataset"])
    dev_answerable = sum(q["split"] == "dev" and q["answerable"] for q in report["dataset"])
    lines = ["# Phase 5 확대 AI 평가 결과", "", f"실행 시작: {report['created_at']} / 완료: {report.get('completed_at', '미완료')}", "",
             f"가상 한국어 규정집 {len(search['documents_sha256'])}개를 대상으로 질문 {len(report['dataset'])}개를 준비했다. 개발용 {dev_count}개로 대안을 선택하고, 최종 확인용 {final_count}개는 설정 선택에 사용하지 않았다.",
             "AI 채점이며 사람 검증은 미완료다. 각 질문·설정의 저장 답변을 별도로 채점했다. 실제 시도·성공·실패·누락 건수는 아래 표에 표시하며, 통계적 유의성이나 실제 기업 문서 성능을 입증하는 결과가 아니다.",
             f"생성 모델: {', '.join(sorted({c['chat_model'] for c in report['configurations'].values()}))}. 채점 모델: {report['judge']['model']}.", "",
             "## 검색 설정 비교", "", f"개발용의 답변 가능한 {dev_answerable}문항 대상이다. 필수 원문 전체 포함률 → 개별 근거 그룹 포함률 → 페이지 적중률 순서로 대안을 고정했다.", "",
             "| 설정 | 청크/중복/k | 페이지 적중 | 필수 원문 전체 포함 | 근거 그룹 포함 |", "| --- | --- | --- | --- | --- |"]
    for name, comparison in search["comparisons"].items():
        c, m = comparison["configuration"], comparison["metrics"]
        chunk = c["index_signature"]["chunking"]
        lines.append(f"| {name} | {chunk['size']}/{chunk['overlap']}/{c['top_k']} | {fraction(m['page_hit_at_k'])} | {fraction(m['complete_quote_coverage'])} | {fraction(m['evidence_group_recall'])} |")
    lines += ["", f"선택한 대안은 **{search['selected_alternative']}**이다. 운영 기본값은 변경하지 않았다.", "", "## 실제 답변 평가", "",
              "| 구분 | 설정 | AI 정답 | 답변 가능한 질문 정답 | 답변 불가 보류 | 평균 응답시간 |", "| --- | --- | --- | --- | --- | --- |"]
    for split, configs in metrics["splits"].items():
        for name, m in configs.items():
            mean = m["latency_ms"]["successful_mean"]
            latency = f"{mean/1000:.2f}초" if mean is not None else "해당 없음 (성공 응답 없음)"
            lines.append(f"| {'개발용' if split == 'dev' else '최종 확인용'} | {name} | {fraction(m['ai_correctness'])} | {fraction(m['ai_answerable_correctness'])} | {fraction(m['abstention_contract'])} | {latency} |")
    lines += ["", "정답률 분모에는 실행·채점 실패와 누락도 포함한다. 응답시간은 검색·생성·검증을 포함하고 초기화·AI 채점·파일 저장은 제외한다. AI가 답변을 보류한 경우도 정상 응답시간에 포함한다. 토큰 사용량은 JSON에 기록하며 비용 금액으로 환산하지 않았다.", "",
              "| 구분 | 설정 | 시도/예정 | 성공 응답 | RAG 오류 | 답변 누락 | 채점 실패·미실행·누락 |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for split, configs in metrics["splits"].items():
        for name, m in configs.items():
            lines.append(f"| {'개발용' if split == 'dev' else '최종 확인용'} | {name} | {m['attempted']}/{m['expected']} | {m['successful']} | {len(m['rag_errors'])} | {len(m['missing'])} | {len(m['judge_errors'])} |")
    lines += ["",
              "| 구분 | 개선된 질문 | 나빠진 질문 | 둘 다 정답 | 둘 다 미통과 |", "| --- | --- | --- | --- | --- |"]
    for split, pair in metrics["paired"].items():
        lines.append(f"| {'개발용' if split == 'dev' else '최종 확인용'} | {', '.join(pair['improved_ids']) or '없음'} | {', '.join(pair['regressed_ids']) or '없음'} | {pair['both_correct']} | {pair['both_not_correct']} |")
    events = [event for event in report.get("execution_events", []) if event["type"] == "checkpoint_write_failure"]
    if events:
        lost = sum(len(event.get("judge_attempts_without_recoverable_response", [])) for event in events)
        saved = events[0] if events else {}
        lines += ["", "## 저장 중단과 복구", "",
                  f"Windows 파일 접근 오류로 중간 저장이 중단되어, 저장된 답변 {saved.get('saved_answers')}개와 채점 {saved.get('recovered_reviews')}개를 복구했다. 응답이 저장되지 않은 채점 {lost}개만 명시적으로 재요청했다. 기존 RAG 답변을 다시 생성하지 않았고 질문·설정 선택·생성 프롬프트·채점 기준은 바꾸지 않았다.",
                  "원래 저장본은 recovery/에 보존했다. 파일 교체 재시도와 채점별 개별 저장을 추가했고 복구 내역·코드 해시는 answers.json의 execution_events에 남겼다. 유실된 채점 응답의 토큰 사용량은 알 수 없어 기록된 토큰 합계를 전체 과금 사용량으로 볼 수 없다.", ""]
    counts = metrics["review_queue"]
    lines += ["", "## 확인이 필요한 답변", "", f"확인 목록은 {counts['entries']}건이다. 의심 답변 {counts['flagged_entries']}건과 AI 통과 표본 {counts['sampled_passes']}건을 포함한다. 동일 질문의 A/B 답변은 별도 건으로 세며 질문 수는 {counts['unique_questions']}개다.", "",
              "[검토용 CSV](review_queue.csv)에는 질문·답변·문제 문장·누락 항목·관련 원문·채점 기준·사람 검토란이 있다. 검색 원문이 부족하다는 이유로 표시된 답변이 반드시 잘못된 주장을 했다는 의미는 아니다.", ""]
    for note in notes["items"]:
        lines += [f"**우선 확인 — {note['id']}/{note['configuration']}:** {note['notes']}", ""]
    for e in queue["items"]:
        if e["reasons"] == ["sample_of_ai_passes"]:
            continue
        lines += [f"### {e['id']} / {e['configuration']} / {e['split']}", "", e["question"], "",
                  "답변: " + (e["answer"] or "실행 오류 또는 누락으로 답변 없음"), "", "확인 사유: " + ", ".join(e["reasons"]), ""]
        for issue in e["issues"]:
            lines.append(f"- {issue['kind']}: {issue['reason']}")
            if issue["answer_span"]: lines.append(f"  문제 문장: {issue['answer_span']}")
            if issue["missing_fact"]: lines.append(f"  누락 항목: {issue['missing_fact']}")
        lines.append("")
    lines += ["## 결과 파일과 재현", "", "- [전체 질문·청크·답변·AI 채점 원본](answers.json)",
              "- [Excel에서 볼 수 있는 답변 목록](answer_results.csv)", "- [설정별 지표](metrics.json)",
              "- [검색 비교와 선택 근거](retrieval_dev.json)", "- [AI 채점 사전 시험](pilot.json)",
              "- [사람 검토 목록 원본](review_queue.json)", "", "```powershell",
              f".\\.venv\\Scripts\\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/{output.name}",
              f".\\.venv\\Scripts\\python.exe -X utf8 -m eval.benchmark summarize --output-dir eval/results/{output.name}",
              f".\\.venv\\Scripts\\python.exe -X utf8 -m eval.render_report --output-dir eval/results/{output.name}", "```", "",
              "위 명령은 저장 결과를 검증·집계·내보내기만 하며 API를 호출하지 않는다. verify는 파일을 변경하지 않는다. 사람 검토, 실제 LangSmith 원격 기록 및 공개 배포는 이번 결과에 포함되지 않는다.", ""]
    write_csv(output / "answer_results.csv", list(answer_rows[0]), answer_rows)
    write_csv(review_csv, list(queue_rows[0]), queue_rows)
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Exported report.md, answer_results.csv, review_queue.csv in {output}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    export(parser.parse_args().output_dir)
