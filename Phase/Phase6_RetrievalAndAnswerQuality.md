# Phase 6 — Retrieval and Answer Quality `✅ Completed Locally`

> Improve complete evidence retrieval and condition-preserving answers with a bounded, auditable context.

**Started**: 2026-10-16 (Asia/Seoul)\
**Completed locally**: 2026-10-16\
**Status**: Implementation and scoped verification complete; opt-in candidate, Cloud mode activation and rollout verification pending.\
**Prerequisites**: Phases 1–4 implemented; Phase 5 demo deployed. The user explicitly deferred remaining Phase 5 checks and authorized Phase 6 documentation, development, and tests.\
**Technology**: Python 3.12, existing E5/Chroma/Claude stack, pytest.

## Scope and tasks

| Task | Work | Acceptance criteria | Verification | Status |
| --- | --- | --- | --- | --- |
| 6.1 | Add an opt-in page-context retrieval mode beside existing chunk retrieval | One vector search; distinct source pages; bounded context; unchanged original page text and accurate source metadata; existing index/bundle reusable | Retrieval, provenance, budget, configuration, and compatibility tests | ✅ |
| 6.2 | Compare existing k=3 and k=5 with bounded page-context candidates | Save full retrievals, configuration, coverage, context size, timing, and failures; never pass reference answers into retrieval | Real local E5 search on the 40 development questions; no generation needed | ✅ 160 searches |
| 6.3 | Strengthen required-item and condition/timing coverage in the answer instruction | Preserve abstention, strict quote checking, and at most one generation; no reference/rubric leakage | Grounding/RAG tests and a small explicit live smoke run if local API access is available | ✅ Six answers and six AI reviews |
| 6.4 | Record results and integrate documentation | English/Korean Phase report and README links; distinguish software tests, retrieval metrics, live observations, and deferred evaluation | Existing full pytest suite, saved Phase 5 artifact verification, deployment bundle check | ✅ 267 tests |

## Design fixed before comparison

- Preserve current default chunk retrieval (k=3), the deployed configuration, PDFs, embeddings, index bundle, and historical Phase 5 results. The improved mode is explicitly selectable; publishing to Cloud is not part of this task.
- The first candidate uses k=5 distinct pages. A second bounded candidate may use k=7. Retrieve up to three times k chunks once, deduplicate by document/page, and construct context from original physical PDF pages. Total text budget: 6,000 characters. Pages that cannot fit are handled without cutting a condition mid-sentence; exact behavior will be documented with implementation.
- Page context is assembled from the runtime PDF corpus after the existing index/PDF integrity checks. Evaluation datasets and annotations are never runtime context. Preserve the original ranked chunk hits separately from the final generation context.
- Prefer this small context-assembly change before changing chunk boundaries: the saved q31/k=5 result contains a duplicate page, while complete original pages can also restore clauses cut at chunk boundaries. No additional embedding model, reranker, hybrid search, or agent loop is planned.
- Compare development complete required-quote coverage first, then evidence-group coverage, and context size. Report regressions and cost proxies explicitly. No claimed accuracy target is invented after seeing results.
- The v2 final split has already been inspected. Do not tune on it or describe it as unseen. This phase uses development diagnostics and known regression cases; a fresh independently held-out set and broad answer evaluation remain future work.
- The current prompt already mentions conditions. The change will make the answer organization explicit: cover each requested item and include the applicable actor, threshold, trigger, deadline, and exception when relevant, with source evidence. This is an instruction improvement, not a local proof of semantic correctness.

## Implementation and usage

`retrieval_context.PageContext` loads the indexed PDF pages once and checks corpus fingerprints before and after extraction. `Retriever` performs one vector search for up to `min(3*k, index_chunk_count)` hits in page mode. It retains the ranked hits in `ranked_chunks` and places the bounded generation context in `retrieved_chunks`. Each source records its original physical page, seed rank/ID, context kind, and a stable page-content hash. Quotes are checked against that delivered context.

If a complete page cannot fit the remaining character budget, use the entire original seed chunk; if that cannot fit, skip it and consider later hits. Never clip a page/chunk mid-condition. A second hit from an already selected page does not consume a source slot. PDF extraction occurs during page-mode initialization; documents are not re-embedded and the index/bundle is unchanged.

`grounding.SYSTEM_PROMPT` now asks for each requested item, its actor/trigger/deadline, applicable threshold, and exception where relevant. This common prompt change also applies to local chunk mode. Source validation and the one-generation limit are unchanged. `eval.evaluate` requires the historical chunks/k=3 mode; `eval.benchmark` explicitly keeps chunk mode so an operator's page-mode setting cannot silently change the old experiment.

New implementation: [retrieval_context.py](../retrieval_context.py), [eval/phase6.py](../eval/phase6.py), [page-context tests](../tests/test_page_context.py), [comparison tests](../tests/test_phase6.py). Configuration and integration changes are in `config.py`, `rag.py`, `grounding.py`, `eval/evaluate.py`, `eval/benchmark.py`, and both example settings files. There are no new dependencies.

Use the selected candidate locally in PowerShell; restart an existing Streamlit process after changing settings:

```powershell
$env:RAG_RETRIEVAL_MODE = "pages"
$env:RAG_TOP_K = "5"
$env:RAG_CONTEXT_MAX_CHARS = "6000"
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

These names also work in server Secrets. Defaults remain `chunks`, `3`, and `6000`; the text budget applies to page mode. Switch to `chunks`/`3` to use the original retrieval behavior. No reindexing is required for these settings.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
# Local embeddings only; use a new output directory for each run.
.\.venv\Scripts\python.exe -X utf8 -m eval.phase6 compare --output-dir eval/results/phase6_new_run
# Billable: up to six answers plus six separate AI reviews; no automatic retries.
.\.venv\Scripts\python.exe -X utf8 -m eval.phase6 smoke --output-dir eval/results/phase6_new_run
```

The comparison requires the existing index and downloaded embedding cache. Every attempt is checkpointed; existing outputs are not overwritten. Smoke execution rejects changed code/dataset/documents/index settings after selection. Questions q01/q08/q31/q54/q09/q10 were chosen as known regression checks, not an independent holdout.

## Results and remaining work

Evidence: [full report](../eval/results/phase6_20261016/report.md), [retrievals](../eval/results/phase6_20261016/retrieval_dev.json), [answers/AI grades](../eval/results/phase6_20261016/smoke.json), [verification](../eval/results/phase6_20261016/verification.json).

| Development retrieval | Complete required quotes | Evidence groups | Multi-document pages | Mean context characters |
| --- | --- | --- | --- | ---: |
| chunks/k=3 | 24/32 | 37/50 | 7/12 | 1,916.23 |
| chunks/k=5 | 26/32 | 43/50 | 10/12 | 3,157.18 |
| **pages/k=5, selected** | **32/32** | **50/50** | **12/12** | **4,242.93** |
| pages/k=7 | 32/32 | 50/50 | 12/12 | 5,791.23 |

All 160 retrieval attempts succeeded. Candidate selection rejects any lost complete-evidence cases versus chunks/k=5, then ranks complete/group coverage and smaller mean context. pages5 gained q25/q28/q29/q30/q31/q32 with no lost cases. Its maximum text was 4,708 characters; average text grew **34.39%** versus chunks5. This is a character-count cost proxy, not a token-price estimate. pages7 provided no additional coverage.

The six live answers and six separate same-model AI grades all succeeded: **6/6 AI-correct**, **4/4 answerable-correct**, **2/2 appropriate abstentions**. q31 now includes both registration deadlines and their starting events; q54 explicitly preserves prior security confirmation in emergencies. Mean RAG latency was **3.50 seconds**, excluding initialization and AI grading. Generation used 36,391 input / 1,776 output tokens; AI grading used 49,314 / 1,754. These known examples are not a general accuracy estimate or human validation.

**267 tests passed in 31.63 seconds** (24 added); the focused run passed 129 tests in 4.97 seconds. `pip check`, the saved Phase 5 benchmark verifier, and the 22-chunk deployment-bundle check passed. All 86 pre-existing evaluation files remain byte-identical. No source PDF, index bundle, `.env`, or Cloud configuration was changed.

Retrieval coverage is not answer correctness. The independent contributions of larger candidate pools, page expansion, and prompt changes were not separately measured. A fresh holdout and broader answer evaluation remain future work. Phase 5 Cloud restart/resource checks, real LangSmith verification, and human review remain deferred. Demo UX, enterprise upload/authentication, and broad operational changes belong to later scope.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-16 | Created the implementation plan before code changes. User authorized development and tests. Separate dev-log skill unavailable; history is maintained here. |
| 2026-10-16 | Implemented opt-in bounded page retrieval and item/condition-preserving answer instructions; selected pages5 on development retrieval, completed 267 tests and six live/AI-reviewed cases, linked evidence and both READMEs. Local scope complete; no Cloud publishing. |

---

# Phase 6 — 검색·답변 품질 개선 `✅ 로컬 완료`

> 길이를 제한하고 근거를 추적할 수 있는 문맥으로 필수 근거 검색과 조건을 보존하는 답변을 개선한다.

**시작일**: 2026-10-16 (한국 시간)\
**로컬 완료일**: 2026-10-16\
**상태**: 구현과 정한 범위의 검증 완료. 선택 가능한 후보이며 Cloud 모드 활성화·원격 반영 확인은 대기 중이다.\
**선행 조건**: Phase 1~4 구현, Phase 5 데모 배포. 사용자가 남은 Phase 5 검증을 보류하고 Phase 6 문서·개발·테스트를 명시적으로 요청했다.\
**기술 구성**: Python 3.12, 기존 E5/Chroma/Claude, pytest.

## 범위와 Task

| Task | 작업 | 완료 기준 | 검증 방법 | 상태 |
| --- | --- | --- | --- | --- |
| 6.1 | 기존 청크 검색에 선택 가능한 페이지 문맥 검색 추가 | 벡터 검색 1회, 중복 페이지 제거, 문맥 길이 제한, 원래 페이지 본문·출처 보존, 기존 인덱스·번들 재사용 | 검색·출처·길이 제한·설정·호환성 테스트 | ✅ |
| 6.2 | 기존 k=3·k=5와 페이지 문맥 후보 비교 | 전체 검색 결과·설정·근거 포함률·문맥 길이·시간·실패 저장. 참고 정답은 검색에 전달하지 않음 | 개발용 40문항의 실제 로컬 E5 검색. 답변 생성 불필요 | ✅ 검색 160회 |
| 6.3 | 요구 항목과 조건·시점을 보존하는 답변 지시 보강 | 보류 원칙·엄격한 원문 인용 검사·최대 생성 1회 유지. 참고 정답·채점 기준 유출 없음 | Grounding/RAG 테스트와 로컬 API가 사용 가능할 때 소수 실제 답변 검사 | ✅ 답변·별도 AI 채점 각 6회 |
| 6.4 | 결과 기록과 문서 연결 | 영문·국문 Phase 및 README 링크. 프로그램 테스트·검색 지표·실제 답변 관찰·보류 평가 구분 | 기존 전체 pytest, Phase 5 저장 산출물 검증, 배포 번들 검사 | ✅ 테스트 267개 |

## 비교 전에 정한 설계

- 현재 기본 청크 검색(k=3), 배포 설정, PDF, 임베딩, 인덱스 번들, Phase 5 과거 결과를 보존한다. 개선 모드는 명시적으로 선택하며 Cloud 게시를 이번 작업에 포함하지 않는다.
- 첫 후보는 서로 다른 페이지 k=5다. 두 번째 제한된 후보는 k=7을 사용할 수 있다. 한 번의 검색으로 최대 k의 3배 청크를 받고 문서·페이지로 중복을 제거한 뒤 원래 PDF 페이지 본문으로 문맥을 구성한다. 전체 본문 한도는 6,000자다. 한도를 넘는 페이지의 조건 문장을 중간에서 자르지 않으며 정확한 처리 방식은 구현과 함께 기록한다.
- 기존 인덱스·PDF 무결성 검사를 거친 실행용 PDF로 페이지 문맥을 구성한다. 평가 데이터·주석을 실행 문맥에 넣지 않는다. 원래 순위의 검색 청크와 최종 생성 문맥을 구분해 보존한다.
- 청크 경계 변경 전에 작은 문맥 구성 개선을 우선한다. 저장된 q31/k=5에는 같은 페이지가 중복되어 있고, 원래 페이지를 사용하면 청크 경계에서 잘린 조항도 복원할 수 있다. 새 임베딩 모델·Reranker·Hybrid Search·에이전트 반복은 계획하지 않는다.
- 개발용 필수 원문 전체 포함률, 개별 근거 그룹 포함률, 문맥 길이 순으로 비교한다. 악화 사례와 비용 관련 대리지표를 공개하며 결과를 보고 정답률 목표를 만들지 않는다.
- v2 최종 확인용 질문은 이미 확인했으므로 튜닝하거나 미공개 평가셋으로 부르지 않는다. 이번에는 개발용 진단과 알려진 회귀 사례를 사용하며 새 독립 평가셋·대규모 답변 평가는 후속 작업이다.
- 기존 프롬프트에도 조건 보존 지시는 있다. 이번에는 질문의 요구 항목별로 답하고, 관련된 주체·기준값·기산점·기한·예외를 근거와 함께 설명하도록 답변 구성을 명확히 한다. 지시 개선이며 의미적 정확성을 로컬 코드로 증명하는 것은 아니다.

## 구현 및 사용법

`retrieval_context.PageContext`는 인덱싱한 PDF 페이지를 한 번 읽고 추출 전후 문서 해시를 검사한다. `Retriever`는 페이지 모드에서 벡터 검색 1회로 최대 `min(3*k, 인덱스 청크 수)`개를 검색한다. 원래 순위는 `ranked_chunks`, 길이를 제한한 생성 문맥은 `retrieved_chunks`에 보존한다. 각 출처에는 실제 페이지, 최초 검색 순위·ID, 문맥 종류, 페이지 내용의 안정적인 해시를 기록한다. 인용은 전달한 문맥과 대조한다.

페이지 전체가 남은 글자 한도에 맞지 않으면 원래 검색 청크 전체를 사용하고, 그것도 맞지 않으면 건너뛴 뒤 후순위 후보를 확인한다. 조건 문장을 중간에서 자르지 않는다. 이미 선택한 페이지의 추가 검색 결과는 출처 슬롯을 차지하지 않는다. 페이지 모드 초기화 때 PDF 본문을 추출하지만 문서를 다시 임베딩하지 않으며 인덱스·번들은 그대로 사용한다.

`grounding.SYSTEM_PROMPT`에 요구 항목별 답, 주체·기산점·기한, 적용 기준과 예외를 명시하도록 지시를 보강했다. 공통 프롬프트 변경이므로 로컬 청크 모드에도 적용된다. 출처 검증과 최대 생성 1회는 유지한다. `eval.evaluate`는 과거 chunks/k=3 모드만 허용하고, `eval.benchmark`는 청크 모드를 명시해 운영자 설정 때문에 과거 실험이 페이지 모드로 바뀌지 않게 했다.

신규 구현: [retrieval_context.py](../retrieval_context.py), [eval/phase6.py](../eval/phase6.py), [페이지 문맥 테스트](../tests/test_page_context.py), [비교 도구 테스트](../tests/test_phase6.py). `config.py`, `rag.py`, `grounding.py`, `eval/evaluate.py`, `eval/benchmark.py`, 설정 예시 2개에 설정·연동을 반영했다. 새 의존성은 없다.

PowerShell에서 선택한 후보를 실행한다. 이미 실행 중인 Streamlit은 설정 변경 후 재시작한다.

```powershell
$env:RAG_RETRIEVAL_MODE = "pages"
$env:RAG_TOP_K = "5"
$env:RAG_CONTEXT_MAX_CHARS = "6000"
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

서버 Secrets에서도 같은 이름을 사용한다. 기본값은 `chunks`, `3`, `6000`이며 본문 한도는 페이지 모드에 적용된다. 기존 검색 방식은 `chunks`/`3`으로 선택한다. 이 설정 변경에는 인덱스 재생성이 필요 없다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
# 로컬 임베딩만 사용. 실행마다 새 출력 폴더 지정.
.\.venv\Scripts\python.exe -X utf8 -m eval.phase6 compare --output-dir eval/results/phase6_new_run
# 과금: 답변 최대 6회 + 별도 AI 채점 최대 6회. 자동 재시도 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.phase6 smoke --output-dir eval/results/phase6_new_run
```

기존 인덱스와 다운로드한 임베딩 캐시가 필요하다. 모든 시도를 중간 저장하고 기존 출력을 덮어쓰지 않는다. 후보 선택 후 코드·데이터·문서·인덱스 설정이 바뀌면 답변 검사를 중단한다. q01/q08/q31/q54/q09/q10은 알려진 회귀 사례이며 독립 평가셋이 아니다.

## 결과와 남은 작업

증빙: [전체 보고서](../eval/results/phase6_20261016/report.md), [검색 원본](../eval/results/phase6_20261016/retrieval_dev.json), [답변·AI 채점](../eval/results/phase6_20261016/smoke.json), [검증 기록](../eval/results/phase6_20261016/verification.json).

| 개발용 검색 | 필수 원문 전체 포함 | 근거 그룹 | 다중 문서 페이지 | 평균 문맥 글자 수 |
| --- | --- | --- | --- | ---: |
| chunks/k=3 | 24/32 | 37/50 | 7/12 | 1,916.23 |
| chunks/k=5 | 26/32 | 43/50 | 10/12 | 3,157.18 |
| **pages/k=5, 선택** | **32/32** | **50/50** | **12/12** | **4,242.93** |
| pages/k=7 | 32/32 | 50/50 | 12/12 | 5,791.23 |

검색 160회 모두 성공했다. 후보 선택은 chunks/k=5의 기존 전체 근거 확보 사례가 하나라도 누락되면 제외하고, 전체·그룹 포함률과 작은 평균 문맥 순으로 판단한다. pages5는 q25/q28/q29/q30/q31/q32를 추가 확보했고 악화는 없었다. 최대 본문은 4,708자이며 평균은 chunks5보다 **34.39% 증가**했다. 글자 수 기준 비용 대리지표이며 토큰 가격 추정이 아니다. pages7의 추가 근거 확보 이득은 없었다.

실제 답변 6회와 같은 모델의 별도 AI 채점 6회가 모두 성공했다. **AI 정답 6/6**, **답변 가능한 질문 정답 4/4**, **적절한 보류 2/2**다. q31은 두 등록 기한과 기산점을 모두 답했고, q54는 긴급 상황에도 보안 사전 확인이 필요함을 명시했다. 평균 RAG 시간은 초기화·채점을 제외한 **3.50초**다. 생성 입력/출력 토큰은 36,391/1,776, AI 채점은 49,314/1,754다. 알려진 사례의 결과로 일반 정답률이나 사람 검증을 뜻하지 않는다.

**전체 테스트 267개·31.63초 통과**(24개 추가). 관련 테스트 먼저 실행한 결과는 129개·4.97초 통과다. `pip check`, Phase 5 저장 평가 검증, 청크 22개 배포 번들 검사도 통과했다. 기존 평가 파일 86개는 바이트 단위로 동일하다. 원본 PDF·인덱스 번들·`.env`·Cloud 설정은 변경하지 않았다.

검색 근거 포함률은 답변 정답률이 아니다. 후보 수 확대·페이지 확장·프롬프트 변경의 개별 기여는 분리 측정하지 않았다. 새 독립 평가셋과 광범위한 답변 평가는 후속 작업이다. Phase 5 Cloud 재시작·자원 검사, 실제 LangSmith, 사람 검토는 계속 보류한다. 데모 사용성, 기업용 업로드·인증, 광범위한 운영 변경은 이후 범위다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-16 | 코드 변경 전에 실행 계획 작성. 사용자가 개발·테스트를 승인했다. 별도 dev-log 스킬 미설치로 이 문서에 변경 이력을 기록한다. |
| 2026-10-16 | 선택형 페이지 문맥 검색과 요구 항목·조건 보존 지시 구현. 개발용 검색으로 pages5 선택, 테스트 267개와 실제 답변·AI 채점 각 6건 완료. 증빙 및 README 2개 연결. 로컬 범위 완료이며 Cloud에는 게시하지 않음. |
