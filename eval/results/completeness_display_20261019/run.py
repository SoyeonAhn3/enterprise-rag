"""One-off regression check: five owner questions and two document-list variants.

Seven answers at most, no retries or judge calls. Run from the project root with
python eval/results/completeness_display_20261019/run.py. A second run is refused.
This is observed-case regression evidence, not a new independent quality score.
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
from grounding import SYSTEM_PROMPT
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

OUT = Path(__file__).resolve().parent


def cases():
    old = {q["id"]: q for q in read(ROOT / "eval/questions_v3.json")}
    specifications = [
        ("owner_01", "v3_d01",
         "비품 공급가액 94만원에 계약상 필수 설치비 6만원이 붙습니다. 이런경우 VAT 포함인지 여부 그리고 결재 기준 총액과 최종 승인자는 어떻게 되나요?",
         ["VAT 제외 기준", "필수 설치비를 합산한 100만원", "팀장 최종 결재"]),
        ("owner_02", "v3_d04",
         "6개월 소프트웨어 계약의 공급가액이 정확히 500만원인데, 이에 대해서 최종 결재, 별도 예산 사전검토, 법무 사전검토",
         ["부서장 결재", "500만원은 금액만으로 재무팀 별도 검토 필수가 아님",
          "예산 미편성·부족이면 금액과 무관하게 재무팀 검토 필요", "법무 검토는 계약 체결 전에 필요"]),
        ("owner_03", "v3_f13",
         "모니터를 주문하고 모니터를 수령했는데, 이후에 해야할 조치에 대해서 안내",
         ["요청 부서가 수령 후 3영업일 이내 검수 등록", "불일치 시 완료 처리하지 않고 시정 요청",
          "IT지원팀이 검수 완료일부터 5영업일 이내 자산번호 부여"]),
        ("owner_04", "v3_f08",
         "검수와 세금계산서는 준비됐는데 지급 요청에서 PO 자료가 빠졌고 공급업체 계좌가 바뀌는 경우 어떻게 해야함",
         ["PO 번호가 포함된 유효한 발주서 첨부", "발주 시 부여한 동일 PO 번호 사용",
          "계좌 확인 자료 첨부를 답변 본문에 명시", "기존 계좌와 달라진 사유", "구매운영팀 확인 기록"]),
        ("owner_05", "v3_f17", "경영지원팀의 남은 잔여예산금액",
         ["등록된 문서에서 해당 정보를 확인할 수 없습니다.", "예산 금액이나 출처를 만들어내지 않음"]),
        ("variant_06", "v3_f08",
         "거래처의 입금 계좌가 변경됐습니다. 지급 요청 전에 어떤 자료와 기록을 준비해야 하나요?",
         ["계좌 확인 자료 첨부를 답변 본문에 명시", "기존 계좌와 달라진 사유", "구매운영팀 확인 기록"]),
        ("variant_07", "v3_f08",
         "계약을 체결하고 검수까지 끝낸 구매 건입니다. 재무팀에 지급을 요청할 때 첨부할 서류를 빠짐없이 알려주세요.",
         ["유효한 발주서와 PO 번호", "계약서", "납품서 또는 완료 보고서", "검수확인서",
          "세금계산서", "공급업체 사업자등록 정보", "계좌 확인 자료"]),
    ]
    selected = []
    for identity, reference, question, criteria in specifications:
        q = deepcopy(old[reference])
        q.update(id=identity, question=question, grading_criteria=criteria,
                 origin="owner_text" if identity.startswith("owner") else "regression_variant")
        # Expected answers from the original wording are not this check's rubric.
        q.pop("expected_answer", None)
        q.pop("split", None)
        if identity in {"variant_06", "variant_07"}:
            groups = {"payment_documents", "bank"} if identity == "variant_06" else {"payment_documents"}
            q["evidence_groups"] = [g for g in q["evidence_groups"] if g["id"] in groups]
        if identity == "owner_03":
            q["additional_observation"] = (
                "The broad owner question does not explicitly request settlement. Observe whether the answer also gives "
                "the five-business-day settlement submission deadline; do not call its omission a new regression."
            )
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
    assert len(selected) == 7
    protocol = seal({
        "created_at": now(), "base_commit": "a8f2032754a29c9765f39639cb370f7813f34128",
        "cases": selected, "source_sha256": hashes(), "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR),
        "answer_prompt": SYSTEM_PROMPT,
        "configuration": public_configuration(settings, read(INDEX_DIR / "manifest.json")),
        "max_answer_calls": 7, "judge_calls": 0, "automatic_retries": 0,
        "reviewer_kind": "codex_source_review_not_independent_human",
        "scope": "Local regression on owner wording and two variants; no independent holdout or causal before/after score.",
        "prior_observation": "The owner-supplied PO answer omitted bank account confirmation material. Full Cloud source excerpts were not supplied.",
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
            print(q["id"], result["status"], "answerable=", result.get("answerable"),
                  "calls=", client.calls, flush=True)
            if result.get("error_type") == "ClaudeError":
                break
    finally:
        if client is not None:
            client.close()
        if retriever is not None:
            retriever.close()
    assert client.calls <= 7
    save_json(OUT / "answers.json", seal({
        "created_at": now(), "protocol_sha256": protocol["sha256"],
        "status": "complete" if len(results) == 7 else "partial", "results": results,
        "answer_calls": client.calls, "judge_calls": 0,
        "source_unchanged": hashes() == protocol["source_sha256"],
        "documents_unchanged": pdf_fingerprints(DOCUMENTS_DIR) == protocol["documents_sha256"],
    }))
    return 0 if len(results) == 7 else 1


if __name__ == "__main__":
    raise SystemExit(main())
