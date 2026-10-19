# Phase 3 — Grounded Answers `✅ Completed`

> Generate Korean answers from retrieved evidence and abstain when the evidence is insufficient.

**Status**: ✅ Completed on 2026-10-14: 167 automated tests passed; real Claude answers, abstentions, and isolated context checks verified.\
**Prerequisites**: [Phase 2](Phase2_IndexingAndRetrieval.md) produces reusable top-three retrieval; a chat model and API access are configured.\
**Technology**: Python 3.12.10, LangChain retrieval, Anthropic Claude Messages API (`anthropic==1.13.0`), pytest.

## Overview

Implemented `RAGAssistant.answer()` in `rag.py`, separate from the UI. Each question performs one retrieval and at most one generation; empty retrieval abstains without calling Claude. There is no query rewriting, repeated retrieval, or automatic generation retry.

Phase 2's 22-chunk index and cached local E5 model are reused. No dependency installation/removal, PDF changes, index rebuild, or `.env` changes were needed in Phase 3.

## Tasks and verified deliverables

| Deliverable | Completion criterion | Verification result |
| --- | --- | --- |
| ✅ Grounded answer | Korean claims use retrieved context and treat document instructions as data | Live q01/q07/q08 claims compared with actual passages; injected document instructions ignored in isolated live checks |
| ✅ Source mapping | Program-assigned IDs map to actual filenames, 1-based pages, and excerpts | Unknown IDs, missing citations, altered amounts/negation, wrong-source quotes, and invented metadata rejected in tests |
| ✅ Abstention | Insufficient evidence produces the fixed statement below and no cited sources | Live q09/q10, partial/conflicting/irrelevant context; empty retrieval skips Claude in an offline test |
| ✅ Callable result | UI/evaluation receive the answer, answerability, claims, validated sources, original retrieval, and latency | `RAGAssistant.answer()`, CLI success/failure/resource cleanup, single-call behavior, and annotation isolation tested |

## Implementation and usage

`grounding.py` owns the system prompt, JSON schema, strict parsing, and local citation validation. Claude returns `answerable` plus `claims`, each with `text` and one or more `{source_id, quote}` entries. The program accepts only complete responses, validates every claim, then appends citation markers and maps IDs to retrieval metadata. It does not silently discard invalid citations or repair malformed output.

The parser rejects extra/duplicate keys, invalid types, uncited claims, unknown IDs, fabricated quotes, and inconsistent abstentions. Quote matching ignores whitespace only and returns the original passage with its line breaks. `sources[].excerpt` retains the first verified quote for compatibility; the UI displays every distinct verified quote from `claims` for each source. Full context remains in `retrieved_chunks`.

| Result field | Meaning |
| --- | --- |
| `question`, `answer`, `answerable` | Validated question, rendered Korean answer, and evidence-based answerability |
| `claims` | Claim text plus locally matched source IDs and original quotes |
| `sources` | Unique cited sources: `source_id`, `document`, 1-based `page`, `chunk_id`, short `excerpt` |
| `retrieved_chunks` | All returned context, including uncited results and distances; default chunks/k=3, optional bounded page mode |
| `retrieval_latency_ms`, `generation_latency_ms`, `latency_ms` | Search, provider call, and complete per-question time; model/index/client initialization excluded |

Normal abstention returns `answerable=false`, empty `claims`/`sources`, and exactly **등록된 문서에서 해당 정보를 확인할 수 없습니다.** API and output-validation failures raise `ClaudeError` or `AnswerValidationError` instead. CLI failures write a sanitized message to stderr and exit with status 1.

```powershell
# Existing retrieval-only CLI remains available without a Claude key.
.\.venv\Scripts\python.exe -X utf8 rag.py "100만원 구매의 최종 결재권자는 누구인가요?"
# Uses the locally configured ANTHROPIC_API_KEY; one billable generation.
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# Five billable generations; saves all results to data/answer_smoke.json.
.\.venv\Scripts\python.exe -X utf8 -m eval.check_answers
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

```python
from config import load_settings
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

settings = load_settings()
client = ClaudeClient(settings)
try:
    retriever = Retriever(settings)
    try:
        assistant = RAGAssistant(retriever, client)
        result = assistant.answer("100만원 구매의 최종 결재권자는 누구인가요?")
        print(result["answer"], result["sources"])
    finally:
        retriever.close()
finally:
    client.close()
```

The caller owns and closes the clients; an interface can reuse them across questions. Each question is independent and sends only its text and retrieved source IDs/text to Claude.

## Verification on 2026-10-14

The full offline suite passed **167 tests in 15.06s**. New coverage is in `test_grounding.py`, `test_answers.py`, `test_answer_checks.py`, and the Claude SDK contract tests. Tests use isolated data and HTTP mocks, never the live API.

`python -m eval.check_answers` passed all five contract checks with `claude-sonnet-5-5`. Claims and actual quotes were also inspected manually. Mean warm-request latency was **3295.44 ms**; individual requests ranged from **1303.55 to 6963.52 ms**. These are five-question smoke measurements, not Phase 5's ten-question score.

| Case | Observed answer and evidence | Latency (ms) |
| --- | --- | ---: |
| q01 | Exactly KRW 1 million → team lead; `02_approval_budget.pdf` p.1, S3 | 2769.08 |
| q07 | KRW 1.8 million laptop → department head and prior security review; approval p.1 S1 + security p.1 S3 | 4079.17 |
| q08 | KRW 7.2 million / 12-month SaaS → CFO and prior legal review; approval p.3 S2 + contract p.1 S1, with approval p.1 S3 for the separate-review caveat | 6963.52 |
| q09 | Cafeteria vegetarian-menu frequency → exact abstention, no citations | 1303.55 |
| q10 | Japan business-trip hotel cap → exact abstention, no citations | 1361.89 |

Four additional live checks used isolated, in-memory context without changing the PDFs/index: a legitimate approval rule with an injected override instruction still produced the supported answer; partial evidence for a compound question, irrelevant text with an instruction to invent an answer, and conflicting rules all abstained. Inputs and outputs are retained locally in `data/grounding_smoke.json`; `data/answer_smoke.json` contains the five real-retrieval cases. Both are ignored by Git.

The q08 retrieval supplies an explicit matching contract example but not the full general legal-review threshold/OR rule. The answer uses that example and does not invent missing thresholds. The broader grading criterion remains a Phase 5 evaluation concern; five smoke checks passing is not a 10/10 correctness claim.

## Final answer and citation improvements — 2026-10-19

Generation instructions now require explicit basic and conditional document lists in the answer, and each claim’s own quotations must retain the responsible actor, action, threshold, timing, exceptions, and estimate qualifiers. Whole-sentence quotation instructions address the observed PDF word-boundary failure. Exact-source validation and the stored answer schema remain unchanged; these instructions do not guarantee semantic completeness automatically.

The [required-item review](../eval/results/completeness_display_20261019/review.json) covers seven live answers, while the [citation review](../eval/results/citation_completeness_20261019/review.json) records four final accepted cases after preserving earlier failures. The latest software run passed **488 tests**. Initial Phase 3 measurements below remain historical; full follow-up evidence is in [Phase 6](Phase6_RetrievalAndAnswerQuality.md#final-portfolio-improvements--2026-10-19).

## Decisions and dependencies

- Use Claude's [JSON structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) via `output_config.format`. Native citation blocks are incompatible with that format, so application-owned IDs and quote validation provide provenance. The model remains configurable.
- Exact quote matching proves provenance, not semantic entailment. Prompt-injection checks are limited examples, not a guarantee; human correctness review remains necessary.
- Retain all returned context independently of cited sources, including the original top-three chunks in default mode. A real filename/page alone does not establish factual support.
- Preserve the 500-character question limit, default 4096 output tokens (configurable from 1 to 4096), 30-second timeout, and zero automatic retries. Limit responses to six claims and validate locally before display. The output default was raised on 2026-10-19 after a recorded truncation at 2048 tokens.
- Evaluation reference answers, evidence annotations, and grading criteria never enter generation. No evaluation-question-specific answers are hard-coded.
- Streamlit, tracing, deployment, and evaluation were subsequently implemented in Phases 4–6. The agreed portfolio scope is complete; see the [current roadmap](DevelopmentStatusAndRoadmap.md). The unavailable `dev-log` skill was skipped; changes are recorded here.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the answer-generation, source-validation, and abstention outline; implementation and checks are pending. |
| 2026-10-14 | User selected Claude plus local multilingual embeddings. Prepared the Claude SDK adapter/settings and verified retrieval handoff; grounded orchestration and live Claude validation remain pending. |
| 2026-10-14 | Verified live Claude model access and short text generation. Grounded orchestration, source validation, and abstention remain the next implementation tasks. |
| 2026-10-14 | Completed structured grounded answers, claim/source validation, abstention, CLI and smoke checker; 167 offline tests, five live retrieval cases, and four isolated live context checks verified. Updated both READMEs; separate dev-log skipped because the skill is unavailable. |
| 2026-10-19 | Synchronized required-item/citation instructions, all-quote display contract, and the 4096-token default with published code; linked focused review and 488-test evidence. Historical measurements retained; dev-log unavailable. |

---

# Phase 3 — 근거 기반 답변 및 출처 검증 `✅ 완료`

> 검색 근거로 한국어 답변을 생성하고 근거가 부족하면 답변을 보류한다.

**상태**: ✅ 2026-10-14 완료. 자동 테스트 167개 통과, 실제 Claude 답변·보류 및 분리된 문맥 검사 검증.\
**선행 조건**: [Phase 2](Phase2_IndexingAndRetrieval.md)의 재사용 가능한 상위 3개 검색, 채팅 모델 및 API 사용 설정.\
**기술**: Python 3.12.10, LangChain 검색, Anthropic Claude Messages API (`anthropic==1.13.0`), pytest.

## 개요

UI와 분리된 `rag.py`에 `RAGAssistant.answer()`를 구현했다. 질문마다 검색 1회와 최대 생성 1회를 수행하며, 검색 결과가 비면 Claude를 호출하지 않고 보류한다. 질문 재작성·재검색·생성 자동 재시도는 없다.

Phase 2의 청크 22개 인덱스와 캐시된 로컬 E5 모델을 재사용했다. Phase 3에서는 패키지 설치·삭제, PDF 변경, 인덱스 재생성, `.env` 변경이 필요하지 않았다.

## Task 및 검증한 산출물

| 산출물 | 완료 기준 | 검증 결과 |
| --- | --- | --- |
| ✅ 근거 기반 답변 | 검색 문맥으로 한국어 주장을 작성하고 문서 속 지시문은 자료로 처리함 | 실제 q01·q07·q08의 주장과 발췌 대조, 분리된 실제 호출에서 문서 지시문 무시 확인 |
| ✅ 출처 매핑 | 프로그램이 부여한 ID가 실제 파일명·1-based 페이지·발췌와 연결됨 | 미등록 ID, 인용 누락, 금액·부정 변경, 다른 출처의 인용문, 조작한 메타데이터 거부 테스트 |
| ✅ 답변 보류 | 근거 부족 시 고정 문구와 빈 인용 목록 반환 | 실제 q09·q10, 일부·상충·무관 근거 확인. 빈 검색은 오프라인 테스트에서 Claude 호출 생략 확인 |
| ✅ 호출 가능한 결과 | UI·평가가 답변, 답변 가능 여부, 주장, 출처, 원래 검색 결과, 시간을 받음 | `RAGAssistant.answer()`, CLI 성공·실패·자원 정리, 단일 호출, 평가 주석 분리 테스트 |

## 구현 및 사용 방법

`grounding.py`가 시스템 프롬프트, JSON 스키마, 엄격한 파싱, 로컬 인용 검증을 담당한다. Claude는 `answerable`과 `claims`를 반환하며 각 주장에 `text`와 `{source_id, quote}` 근거를 포함한다. 프로그램은 완성된 응답의 모든 주장을 검증한 뒤 인용 표시를 붙이고 검색 메타데이터에서 파일명·페이지를 가져온다. 잘못된 인용을 조용히 버리거나 응답을 자동으로 보정하지 않는다.

추가·중복 키, 잘못된 타입, 인용 없는 주장, 미등록 ID, 조작한 인용문, 주장과 함께 반환한 보류를 거부한다. 인용문 대조에서는 공백만 무시하고 원문 줄바꿈을 복원한다. `sources[].excerpt`에는 호환성을 위해 출처별 첫 인용문을 보존하며, 화면에는 `claims`의 출처별 서로 다른 검증된 인용문을 모두 표시한다. 전체 검색 문맥은 `retrieved_chunks`에 보존한다.

| 반환 필드 | 의미 |
| --- | --- |
| `question`, `answer`, `answerable` | 검증한 질문, 한국어 답변, 근거에 따른 답변 가능 여부 |
| `claims` | 주장과 로컬에서 대조한 출처 ID·원문 인용 |
| `sources` | 중복 제거한 인용 출처: `source_id`, `document`, 1-based `page`, `chunk_id`, 짧은 `excerpt` |
| `retrieved_chunks` | 인용하지 않은 결과·거리를 포함한 검색 문맥 전체. 기본 chunks/k=3이며 길이를 제한한 페이지 모드도 지원 |
| `retrieval_latency_ms`, `generation_latency_ms`, `latency_ms` | 검색, API 호출, 질문 전체 처리 시간. 모델·인덱스·클라이언트 초기화 제외 |

정상적인 보류는 `answerable=false`, 빈 `claims`·`sources`, 정확히 **등록된 문서에서 해당 정보를 확인할 수 없습니다.**를 반환한다. API 및 출력 검증 실패는 각각 `ClaudeError`, `AnswerValidationError` 예외로 구분한다. CLI 실패는 민감 정보를 제외한 메시지를 stderr에 쓰고 종료 코드 1을 반환한다.

```powershell
# 기존 검색 전용 명령: Claude 키 불필요
.\.venv\Scripts\python.exe -X utf8 rag.py "100만원 구매의 최종 결재권자는 누구인가요?"
# 로컬 ANTHROPIC_API_KEY 사용, 과금되는 생성 1회
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# 과금되는 생성 5회, data/answer_smoke.json에 전체 결과 기록
.\.venv\Scripts\python.exe -X utf8 -m eval.check_answers
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

```python
from config import load_settings
from llm import ClaudeClient
from rag import RAGAssistant, Retriever

settings = load_settings()
client = ClaudeClient(settings)
try:
    retriever = Retriever(settings)
    try:
        assistant = RAGAssistant(retriever, client)
        result = assistant.answer("100만원 구매의 최종 결재권자는 누구인가요?")
        print(result["answer"], result["sources"])
    finally:
        retriever.close()
finally:
    client.close()
```

호출자가 클라이언트를 생성·종료하며 화면에서는 질문 사이에 재사용할 수 있다. 질문마다 독립적으로 질문 텍스트와 검색된 출처 ID·본문만 Claude에 전달한다.

## 2026-10-14 검증 결과

전체 오프라인 테스트 **167개가 15.06초에 통과**했다. 신규 검증은 `test_grounding.py`, `test_answers.py`, `test_answer_checks.py`, Claude SDK 계약 테스트에 있다. 테스트는 분리된 데이터와 HTTP 모의 응답을 사용하며 실제 API를 호출하지 않는다.

`python -m eval.check_answers`로 `claude-sonnet-5-5`의 5문항 계약 검사를 모두 통과했고, 주장과 실제 인용문도 수동 대조했다. 초기화 후 질문 처리 시간은 평균 **3295.44 ms**, 범위 **1303.55~6963.52 ms**였다. Phase 5의 10문항 점수가 아닌 5문항 동작 측정이다.

| 사례 | 실제 답변 및 근거 | 시간(ms) |
| --- | --- | ---: |
| q01 | 정확히 100만원 → 팀장. `02_approval_budget.pdf` 1쪽 S3 | 2769.08 |
| q07 | 180만원 노트북 → 부서장·사전 보안검토. 결재 1쪽 S1 + 보안 1쪽 S3 | 4079.17 |
| q08 | 720만원·12개월 SaaS → CFO·법무 사전검토. 결재 3쪽 S2 + 계약 1쪽 S1, 별도 사전검토 설명은 결재 1쪽 S3 | 6963.52 |
| q09 | 식당 채식 메뉴 횟수 → 고정 보류 문구, 인용 없음 | 1303.55 |
| q10 | 일본 출장 숙박비 상한 → 고정 보류 문구, 인용 없음 | 1361.89 |

추가 실제 호출 4개는 PDF·인덱스를 변경하지 않는 메모리 문맥으로 검증했다. 정상 결재 규정에 답변 조작 지시문을 붙여도 근거 있는 답변을 유지했다. 복합 질문에 일부 근거만 제공한 경우, 무관한 문서에서 답을 지어내라고 명령한 경우, 서로 충돌하는 규정은 모두 보류했다. 입력과 출력은 로컬 `data/grounding_smoke.json`, 실제 검색 5문항은 `data/answer_smoke.json`에 보존했고 두 파일 모두 Git에서 제외했다.

q08은 질문과 일치하는 계약 사례를 검색했지만 일반적인 법무 검토 기준 금액·기간과 OR 규칙 전체는 검색되지 않았다. 답변은 해당 사례만 활용하고 빠진 기준을 지어내지 않는다. 이와 관련된 전체 채점 기준은 Phase 5에서 평가할 항목이며, 5개 동작 검사를 통과했다고 정답률 10/10을 주장하지 않는다.

## 최종 답변 및 인용 개선 — 2026-10-19

답변 본문에 기본·조건부 필수 서류를 명시하고, 주장별 인용문에 담당자·행동·금액 기준·시점·예외·예상 기간 단서를 보존하도록 생성 지시를 보완했다. PDF 단어 중간부터 인용한 사례에는 문장 전체 인용 지시를 추가했다. 원문 일치 검증과 저장 답변 형식은 유지하며, 이 지시가 의미적 완전성을 자동으로 보장하지는 않는다.

[필수 항목 검토](../eval/results/completeness_display_20261019/review.json)는 실제 답변 7개, [인용 검토](../eval/results/citation_completeness_20261019/review.json)는 이전 실패를 보존한 뒤 최종 4사례의 통과를 기록한다. 최신 소프트웨어 테스트는 **488개 통과**다. 최초 Phase 3 측정값은 당시 기록으로 유지하며 전체 후속 증빙은 [Phase 6](Phase6_RetrievalAndAnswerQuality.md#최종-포트폴리오-개선--2026-10-19)에 있다.

## 결정 사항 및 의존성

- Claude의 [JSON 구조화 출력](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)을 `output_config.format`으로 사용한다. 네이티브 인용 블록과는 호환되지 않으므로 프로그램의 ID·인용문 검증으로 출처를 확인한다. 모델은 설정 가능하게 유지했다.
- 인용문 일치는 원문 출처를 증명하며 주장과 근거의 의미적 일치까지 보장하지 않는다. 지시문 방어 검사는 제한된 사례 검증이므로 정확성에 대한 사람의 검토가 필요하다.
- 인용한 출처와 별개로 검색 문맥 전체를 보존하며 기본 모드에서는 원래 상위 3개 청크를 포함한다. 실제 파일·페이지가 있다는 것만으로 사실의 근거가 충분한 것은 아니다.
- 질문 500자, 기본 출력 4096토큰(1~4096 설정 가능), 요청 제한 30초, 자동 재시도 0회를 유지한다. 주장은 최대 6개이며 표시 전에 로컬 검증한다. 2048토큰에서 잘린 답변을 기록한 뒤 2026-10-19 출력 기본값을 높였다.
- 평가 참고 정답·근거 주석·채점 기준을 생성에 전달하지 않으며 평가 질문별 정답을 코드에 넣지 않는다.
- Streamlit·실행 추적·배포·평가는 이후 Phase 4~6에서 구현했다. 합의한 포트폴리오 범위는 완료했으며 [최신 로드맵](DevelopmentStatusAndRoadmap.md)을 따른다. `dev-log` 스킬이 없어 별도 기록은 생략하고 이 문서에 변경 이력을 기록한다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 답변 생성·출처 검증·답변 보류의 개요 신규 작성. 구현과 검증은 미실행 상태로 기록함. |
| 2026-10-14 | 사용자가 Claude·로컬 다국어 임베딩을 선택함. Claude SDK 어댑터·설정 및 검증된 검색 전달 준비. 근거 기반 연결과 실제 Claude 검증은 대기. |
| 2026-10-14 | 실제 Claude 모델 접근과 짧은 텍스트 생성 검증. 근거 기반 연결·출처 검증·답변 보류는 다음 구현 대상. |
| 2026-10-14 | 구조화된 근거 답변·주장 및 출처 검증·답변 보류·CLI·동작 검사 구현 완료. 오프라인 테스트 167개, 실제 검색 5문항, 분리된 실제 문맥 검사 4개 검증. 양쪽 README 갱신. dev-log 스킬 부재로 별도 로그 생략. |
| 2026-10-19 | 게시한 코드에 맞춰 필수 항목·인용 지시, 모든 인용 표시 계약, 기본 출력 4096토큰을 반영하고 집중 검토·테스트 488개 증빙을 연결했다. 과거 측정값 보존, 별도 dev-log 미설치. |
