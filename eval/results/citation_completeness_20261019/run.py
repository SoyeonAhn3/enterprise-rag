"""Four observed-case citation checks; no judge, retries or independent holdout.

Run once from the project root. The prior answer artifacts remain unchanged.
Criteria are recorded before generation and never included in the model input.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from config import DOCUMENTS_DIR, INDEX_DIR, load_settings, pdf_fingerprints
from eval.benchmark import answer_once, now, read, seal
from eval.evaluate import public_configuration, save_json
from grounding import SYSTEM_PROMPT, answer_schema
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

OUT = Path(__file__).resolve().parent


def cases():
    old = {q["id"]: q for q in read(ROOT / "eval/questions_v3.json")}
    owner = read(ROOT / "eval/results/completeness_display_20261019/attempts/owner_04.json")["payload"]
    specifications = [
        ("threshold", "v3_f03", old["v3_f03"]["question"],
         "eval/results/v3_closeout_20261019/final/v3_f03.json",
         ["VAT 제외 필수 설치비 합산으로 300만원", "300만원 이상이면 서로 다른 공급업체의 유효 견적 2부 이상 원칙",
          "100만원 초과 500만원 이하의 최종 결재권자는 부서장"],
         "비교견적 claim의 인용 자체에 300만원 이상 조건과 서로 다른 공급업체의 유효 견적 2부 이상 규칙이 모두 있어야 함"),
        ("timing", "v3_f05", old["v3_f05"]["question"],
         "eval/results/v3_closeout_20261019/final/v3_f05.json",
         ["개인정보 위탁은 금액·기간과 무관하게 계약 체결 전에 법무지원팀 및 DPA 검토 필요",
          "발주·계약 전 정보보안팀 검토", "높음 위험도 5영업일 예상, 서류 완비 시점부터 계산",
          "보완 시 연장 가능하며 법적 기한·승인 보장은 아님"],
         "법무 검토 claim의 인용 자체에 계약 체결 전 시점과 개인정보 위탁의 적용 조건이 모두 있어야 함"),
        ("actor", "v3_f08", owner["question"] + ". PO 발행 담당 부서와 이후 단계에서도 같은 번호를 쓰는지도 알려주세요.",
         "eval/results/completeness_display_20261019/attempts/owner_04.json",
         ["유효한 발주서와 PO 번호 보완", "계좌 확인 자료를 답변 본문에 명시",
          "기존 계좌와 달라진 사유 및 구매운영팀 확인 기록", "구매운영팀이 발주서를 발행하고 검수·정산에서도 같은 PO 번호 사용"],
         "PO 담당 주체 claim의 인용 자체에 구매운영팀과 발주서 발행 행위가 있어야 하며 동일 PO 번호 유지 주장에도 대응 인용이 있어야 함"),
        ("abstention", "v3_f17", "경영지원팀의 남은 잔여예산금액",
         "eval/results/completeness_display_20261019/attempts/owner_05.json",
         ["등록된 문서에서 해당 정보를 확인할 수 없습니다.", "claims와 sources가 비어 있어야 함"],
         "문서에 없는 금액은 생성하지 않음"),
    ]
    selected = []
    for identity, reference, question, baseline, criteria, focus in specifications:
        q = deepcopy(old[reference])
        q.pop("expected_answer", None)
        q.pop("split", None)
        q.update(id=identity, question=question, baseline_artifact=baseline,
                 baseline_sha256=hashlib.sha256((ROOT / baseline).read_bytes()).hexdigest(),
                 required_answer_facts=criteria, citation_focus=focus,
                 wording="explicit_actor_request_added" if identity == "actor" else "previously_observed_question")
        selected.append(q)
    return selected


def hashes():
    files = [*ROOT.glob("*.py"), *(ROOT / "eval").glob("*.py"), *(ROOT / "tests").glob("*.py"), Path(__file__)]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}


class RecordingClaude(ClaudeClient):
    calls = 0
    raw = None

    def generate(self, *args, **kwargs):
        self.raw = None
        self.calls += 1
        self.raw = super().generate(*args, **kwargs)
        return self.raw


def main():
    folder = OUT / "attempts"
    folder.mkdir(exist_ok=False)
    settings = replace(load_settings(), retrieval_mode="pages", top_k=5, context_max_chars=6000,
                       embedding_local_files_only=True, langsmith_tracing=False)
    selected = cases()
    assert len(selected) == 4
    protocol = seal({
        "created_at": now(), "base_commit": "a8f2032754a29c9765f39639cb370f7813f34128",
        "cases": selected, "source_sha256": hashes(), "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR),
        "answer_prompt": SYSTEM_PROMPT, "answer_schema": answer_schema(5),
        "configuration": public_configuration(settings, read(INDEX_DIR / "manifest.json")),
        "max_answer_calls": 4, "judge_calls": 0, "automatic_retries": 0,
        "reviewer_kind": "codex_source_review_not_independent_human",
        "scope": "Known-case regression, with an explicit PO actor request added to the owner wording. Not a holdout or a causal before/after accuracy score.",
        "review_rules": [
            "Check all required answer facts; abstention or deleting a required fact does not fix a citation gap.",
            "Review each claim against only its own quotes and the question's scenario facts, then check the original PDF context.",
            "Record any new citation gaps, missing facts or errors without retries or replacement answers.",
        ],
    })
    save_json(OUT / "protocol.json", protocol)
    client, retriever, results = None, None, []
    try:
        client = RecordingClaude(settings)
        retriever = Retriever(settings)
        assistant = RAGAssistant(retriever, client)
        for q in selected:
            assert hashes() == protocol["source_sha256"], "Code changed during execution."
            target = folder / f"{q['id']}.json"
            pending = seal({"state": "pending", "started_at": now(), "question_id": q["id"],
                            "protocol_sha256": protocol["sha256"]})
            assert not target.exists()
            save_json(target, pending)
            client.raw, client.last_usage = None, None
            before_calls = client.calls
            result = answer_once(assistant, q)
            result.update(raw_response=client.raw, answer_calls=client.calls - before_calls)
            save_json(target, seal({**pending, "state": "completed", "completed_at": now(), "payload": result}))
            results.append(result)
            print(q["id"], result["status"], "answerable=", result.get("answerable"), "calls=", client.calls, flush=True)
            if result.get("error_type") == "ClaudeError":
                break
    finally:
        if client is not None:
            client.close()
        if retriever is not None:
            retriever.close()
    assert client.calls <= 4
    save_json(OUT / "answers.json", seal({
        "created_at": now(), "protocol_sha256": protocol["sha256"],
        "status": "complete" if len(results) == 4 else "partial", "results": results,
        "answer_calls": client.calls, "judge_calls": 0,
        "source_unchanged": hashes() == protocol["source_sha256"],
        "documents_unchanged": pdf_fingerprints(DOCUMENTS_DIR) == protocol["documents_sha256"],
    }))
    return 0 if len(results) == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
