# Development Status and Roadmap

**Reviewed**: 2026-10-16 (Asia/Seoul)\
**Current milestone**: Phases 1–4 verified locally; Phase 6 implemented and verified locally, with Cloud settings/reboot reported complete by the owner. Real local-to-remote tracing is verified; 120 comparison answers were attempted, while 87 failed AI reviews are deferred by the owner after API credit exhaustion.\
**Planning assumption**: The user clarified that this project demonstrates RAG understanding, implementation, precision, and measured accuracy. Concurrency testing is excluded from the current scope and Phase 7 usability remains deferred.

The initial implementation in the [Phase 6 report](Phase6_RetrievalAndAnswerQuality.md) records 267 passing tests, development complete-evidence retrieval of 32/32 with optional pages/k=5, and six known live cases passing same-model AI review. Code was pushed as [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa). The owner reported setting pages/5/6000 and rebooting Cloud; effective runtime behavior has not been independently checked. The original Phase 5 audit below is preserved as historical evidence.

## Project objective and evidence priorities

Demonstrate that the developer can explain and implement PDF extraction, chunking, embeddings, retrieval, context construction, grounded generation, and source validation; measure how often the complete required evidence and correct answer are obtained; and explain improvements and remaining failures. Streamlit is the demonstration interface. Production adoption, concurrent-user capacity, UI expansion, and enterprise operations are not current completion requirements.

The follow-up implemented stronger tracing, a frozen paired evaluator, offline auditing, and review-only recovery. Real trace verification passed in the earlier iteration; the latest offline work passes 347 tests. Coverage first improved from chunks 37/48 to pages 47/48, then to 48/48 with final-page selection; full answer accuracy remains unestablished because grading is incomplete. Traces help explain why an answer happened; reference questions, scoring rules, and review establish answer quality. Report retrieval coverage, answer correctness, evidence support/condition completeness, and appropriate abstention separately. Keep software tests, known-case AI grades, human review, and independent evaluation distinct. The owner chose not to recharge now; keep the 87-item recovery plan offline until grading is explicitly resumed.

## Original Phase 5 audit (historical)

The local application already performs the complete PDF → search → grounded Korean answer → source display flow. The public demo was deployed to Streamlit Community Cloud on 2026-10-16 ([enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/)). The current evidence priorities are real trace verification, broader answer-quality measurement, and an explanation of retrieval/generation failures and improvements. Earlier deployment-operation proposals remain historical or optional; enterprise document administration and access control are not implemented.

This review checked source code, existing Phase reports, saved evaluation artifacts, and the local Python environment. The fresh checks below are offline. Live Claude answers and browser screenshots are historical evidence from 2026-10-14; this audit did not repeat those calls or inspect the remote GitHub/Cloud deployment.

| Area | Implemented behavior and evidence | Status |
| --- | --- | --- |
| Phase 1: documents | `ingest.py` extracts physical pages, creates stable chunk IDs, and excludes evaluation data; 4 PDFs, 13 pages, 22 chunks | Locally complete |
| Phase 2: retrieval | `embeddings.py`, `index_store.py`, `rag.py`: local E5 embeddings, persistent Chroma, integrity checks, compatible reuse, explicit rebuild | Locally complete; effective k=3 |
| Phase 3: answers | `RAGAssistant.answer()` retrieves once and makes at most one Claude call; `grounding.py` validates JSON, source IDs, and original quotes; insufficient evidence causes abstention | Locally complete; semantic completeness remains a quality limitation |
| Phase 4: interface | `app.py`, `app_runtime.py`, `source_display.py`: examples, session chat, citations, excerpts, errors, latency, cached resources, ten-attempt limit | Locally complete; real browser evidence already saved |
| Phase 5: evaluation | Original ten-question baseline plus 60-question comparison, 120 answers/AI grades, reproducible metrics, checkpoint recovery, protected review exports | Implemented and reproduced |
| Phase 5: tracing | `tracing.py` separates retrieval/generation and isolates tracing failures; `eval/check_trace.py` can read back the remote run tree | Implemented; real verification pending |
| Phase 5: deployment | `deployment.py`, portable vector bundle, Streamlit settings, deployment guide | Deployed 2026-10-16 ([public URL](https://enterprise-rag-demo-project.streamlit.app/)); owner's private-window check only. Cloud restart, startup time, and memory unverified |
| Human review | 34 queue entries: 26 flagged answers and 8 sampled passes across 23 questions | Deferred; AI scores are not human validation |

Phase implementation records: [1](Phase1_Foundation.md), [2](Phase2_IndexingAndRetrieval.md), [3](Phase3_GroundedAnswers.md), [4](Phase4_StreamlitInterface.md), [5](Phase5_EvaluationAndDeployment.md).

## Historical verification before Phase 6 on 2026-10-16

| Check | Observed result |
| --- | --- |
| Full existing test suite | **243 passed in 60.40 seconds**, exit code 0 |
| Python / dependencies | Python 3.12.10; `pip check`: no broken requirements |
| In-memory corpus preparation | 4 documents, 13 text pages, 0 skipped pages, 22 chunks |
| Saved benchmark verification | 60 questions, 120 answers, 120 reviews; no RAG errors, missing answers, or judge errors/missing grades in that saved run |
| Deployment bundle | Valid; 22 chunks; same bundle checksum as the previous verification |
| Effective local configuration | 800-character chunks, 120 overlap, k=3; Claude key present, without testing current API access |
| Real trace readiness | Tracing disabled, LangSmith key absent, local `data/trace_check.json` absent |
| CI | No `.github/workflows/` directory in this project |

See the [dated verification record](../eval/results/phase5_v2_20261014/verification_20261016.json). Tests verify software behavior; they do not establish answer correctness. These checks generated no new model answers or AI grades.

## What the quality results imply

The [saved expanded evaluation](../eval/results/phase5_v2_20261014/report.md) compared A (800/120/k=3) with B (800/120/k=5), selected using development retrieval only.

| Measure | A: current default | B: evaluated candidate |
| --- | --- | --- |
| Development AI correctness | 35/40, 87.5% | 39/40, 97.5% |
| Final-check AI correctness | 13/20, 65.0% | 15/20, 75.0% |
| Final-check correctness on answerable questions | 9/16, 56.25% | 11/16, 68.75% |
| Final-check complete required-quote coverage | 9/16, 56.25% | 11/16, 68.75% |
| Final-check multi-document page coverage | 1/6 | 3/6 |
| Final-check abstention on unanswerable questions | 4/4 | 4/4 |
| Development mean / p95 RAG latency | 3.00 / 4.35 seconds | 3.44 / 6.09 seconds |

These are single-run synthetic results graded by the same model used for generation. The historical ten-question score of 90% should not stand alone as the current quality summary. B improved six paired answers across both splits with no observed regressions, but its development generation input tokens rose from 133,049 to 185,176, about 39%. This is token usage, not a monetary cost estimate or proof that B is always slower.

The evidence supports three priorities:

1. **Retrieve all required clauses.** q31/B missed the acceptance-registration deadline and correctly abstained from the incomplete context. That is an end-to-end retrieval failure, not a reason to weaken the abstention rule. Final multi-document coverage also remains limited with k=5.
2. **Preserve conditions and timing.** q08/A has disputed rubric completeness; q54/B omits the emergency-specific prior-confirmation rule. Exact quote matching proves provenance, not that every answer requirement was satisfied.
3. **Separate model failures from review limitations.** Some AI notes call a context-appropriate abstention “wrong” because the full corpus contains the answer. Future analysis should distinguish retrieval insufficiency, generation omissions, and ambiguous grading. Keep the existing grades unchanged as historical evidence.

`RAG_TOP_K` is supported by `config.load_settings()` and the dynamic source schema; changing only k does not require rebuilding the index because k is outside `index_signature()`. Both example settings files now explicitly contain `RAG_TOP_K=3`. Phase 6 adds opt-in `RAG_RETRIEVAL_MODE=pages` and a context budget; its selected candidate is pages/k=5. Publishing that candidate is separate from the completed local implementation.

## Development order

The latest [Phase 6 results and limits](Phase6_RetrievalAndAnswerQuality.md#validation-diagnostics-and-evidence-selection) supersede earlier release proposals. The initial audit above is historical; its missing-key/trace status is no longer current.

| Priority | Remaining work | Reason and current status |
| --- | --- | --- |
| Completed locally | Safe validation-rule and field-location records | Runtime/evaluators retain rule/path and response length/hash. Strict checks remain; four historical causes are unavailable because the original details were not recorded. |
| Completed locally | Improve final evidence selection | A constrained final-slot replacement recovers q51 rank 9. Same-candidate offline coverage improves 47/48 to 48/48, with no complete-evidence regressions. New answer accuracy is unmeasured. |
| Deferred by owner | Recover 87 failed AI reviews | API credit exhaustion was confirmed; the owner chose not to recharge now. Saved answers and an offline recovery plan allow judge-only continuation later. No new model calls are authorized during this deferral. |
| Deferred human review | Preserve the existing 34-entry queue | AI review is not human validation. Resume only when the owner requests it; preserve earlier scores and notes. |
| Future quality evidence | Prepare fresh independent questions before another accuracy claim | All 60 current cases were previously inspected. Freeze questions, references and scoring before implementation changes or evaluation. |
| Optional supporting work | Cloud resource checks, CI and SDK maintenance | Useful later; not current RAG demonstration requirements. |
| Explicitly deferred/excluded | Phase 7 usability / concurrency testing | Usability remains deferred; concurrent-user testing is outside the goal. |

## Immediate work sequence and decisions

**Completed locally:** trace hierarchy and token metadata fixes, real pages/5/6000 remote readback, paired 120-answer attempt records, offline artifact verification, review recovery preparation, validation diagnostics, final-page selection, and 347 passing tests. The earlier answer comparison obtained complete required context in 37/48 chunk cases and 47/48 page cases; the latest retrieval-only selection check reaches 48/48. In the earlier answer run, validated response counts were 59/60 and 57/60. Grading completed only 15/59 and 14/57 eligible responses. Do not turn the raw 14/60 confirmed-pass counts into an accuracy estimate.

**Latest owner decision:** do not recharge now; defer the remaining 87 AI reviews. Recovery preparation made no API calls. Do not execute its `run` command until the owner resumes grading. The [prepared plan](../eval/results/phase6_review_recovery_selection_20261016/plan.json) targets only failed reviews of saved successful answers. It replaces the prior plan for future execution because source hashes changed; the prior plan is preserved. Those future grades will assess old answers, not the new selector. If recovery encounters another provider failure, it stops at the first error; earlier results remain intact.

Keep owner-reported Cloud pages/5/6000 settings/reboot separate from verified local execution. This revision packages the completed follow-up for GitHub publication through the separate enterprise-rag checkout. Development and verification were local; Cloud behavior remains unverified for this revision. The answer prompt is unchanged; the new selection heuristic was evaluated on known cases, so fresh independent questions remain the next priority. Explain the measured tradeoff and remaining failures using the Phase 6 evidence, and retain human-review/fresh-holdout limitations.

## Reproducible local checks

Run from the project root using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.selection verify --output-dir eval/results/phase6_selection_20261016
.\.venv\Scripts\python.exe -X utf8 deployment.py check
```

For future Cloud setup, select the repository, branch, entrypoint, Python version, and server secrets using [Streamlit's official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). LangSmith's [official instrumentation guide](https://docs.langchain.com/langsmith/annotate-code) explains trace configuration and hierarchy. These references were checked on 2026-10-16; neither establishes that this app has been deployed. Project-specific acceptance steps remain in [DEPLOYMENT.md](../DEPLOYMENT.md).

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-16 | Created a source-backed status audit, refreshed offline evidence, and proposed a staged roadmap. No runtime changes, new model evaluation, deployment, or human grading. Separate dev-log unavailable; history recorded here. |
| 2026-10-16 | Recorded the Streamlit Community Cloud deployment and public URL; the repository was made public. Documentation only; runtime code, settings, and evaluations unchanged. Formal Cloud acceptance checks and the real trace remain pending. |
| 2026-10-16 | Applied the user's decision to defer Phase 5 checks; recorded local Phase 6 completion and evidence. Corrected the stale claim that the example settings omit RAG_TOP_K. No Cloud publishing. |
| 2026-10-16 | Recorded b89ed76 publication and the decision to activate Phase 6 pages/5/6000 first. Explicitly deferred Phase 7 usability; other checks remain pending. Cloud Settings access is unavailable in this session, so activation is not claimed. Documentation only; separate dev-log unavailable. |
| 2026-10-16 | Recorded owner-reported settings/reboot completion. Reframed priorities around demonstrating RAG understanding, measured accuracy, evidence precision, and explained improvements; excluded concurrency testing and retained the usability deferral. Tracing and evaluation remain proposed work, not completed runs. Separate dev-log unavailable. |
| 2026-10-16 | Recorded verified LangSmith, 305 tests, retrieval coverage 37/48 versus 47/48, incomplete AI grading, the owner's no-recharge deferral, and offline recovery preparation. Prioritized failure-detail capture, evidence selection, and later independent evaluation. No push or new live calls after deferral; dev-log unavailable. |
| 2026-10-16 | Completed validation diagnostics and final-page selection offline; 347 tests, coverage 48/48, no complete-evidence regressions. Prepared a current-source 87-review plan without running it; retained old evidence and deferred paid grading. Next priority: fresh independent questions. |

---

# 개발 현황 및 향후 개발 계획

**점검일**: 2026-10-16 (한국 시간)\
**현재 단계**: Phase 1~4 로컬 검증 완료. Phase 6 로컬 구현·검증 완료 및 사용자 보고 기준 Cloud 설정·Reboot 완료. 로컬 실행의 실제 원격 추적은 검증했다. 비교 답변 120건을 시도했으며 API 잔액 부족 후 AI 채점 실패 87건은 사용자 결정으로 보류한다.\
**계획 전제**: 사용자가 목표를 RAG 이해·구현·정교함·측정한 정확도를 보여주는 것으로 명확히 했다. 동시 접속 검사는 현재 범위에서 제외하며 Phase 7 사용성은 계속 보류한다.

[Phase 6 보고서](Phase6_RetrievalAndAnswerQuality.md)의 최초 구현 결과에 테스트 267개 통과, 선택형 pages/k=5의 개발용 필수 근거 전체 확보 32/32, 알려진 실제 사례 6건의 같은 모델 AI 채점 통과를 기록했다. 코드는 [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa)으로 푸시했다. 사용자는 Cloud에 pages/5/6000 설정을 적용하고 Reboot했다고 보고했으며 실제 실행 동작은 별도로 확인하지 않았다. 아래 기존 Phase 5 점검은 과거 증빙으로 보존한다.

## 프로젝트 목표와 증빙 우선순위

PDF 추출·청크 분할·임베딩·검색·문맥 구성·근거 기반 생성·출처 검증을 이해하고 구현했음을 설명한다. 필요한 근거와 올바른 답변을 얼마나 자주 얻는지 측정하고, 개선 이유와 남은 실패를 제시한다. Streamlit은 시연 화면이다. 실제 사용자 확보, 동시 접속 규모, UI 확장, 기업용 운영은 현재 완료 요건이 아니다.

후속에서 추적 보강·기준 고정 비교·오프라인 감사·채점만 복구하는 도구를 구현했다. 이전 작업에서 실제 추적 검증이 통과했고 최신 오프라인 작업은 테스트 347개가 통과했다. 근거 확보는 청크 37/48에서 페이지 47/48, 마지막 페이지 선택 개선 후 48/48로 늘었으나 채점 미완료로 전체 답변 정확도는 확정하지 않는다. 추적은 답변이 나온 과정을 설명하고, 정답이 정해진 질문·채점 기준·검토는 답변 품질을 평가한다. 검색 근거 확보율, 답변 정확도, 근거 일치·조건 완전성, 적절한 보류를 나누어 보고한다. 프로그램 테스트, 알려진 사례의 AI 채점, 사람 검토, 독립 평가를 구분한다. 사용자는 지금 충전하지 않기로 했으므로 채점을 명시적으로 재개할 때까지 87건 복구 계획은 오프라인으로 유지한다.

## 최초 Phase 5 현황 점검 (과거 기록)

로컬에서는 PDF → 검색 → 근거 기반 한국어 답변 → 출처 표시의 전체 흐름이 동작한다. 2026-10-16 Streamlit Community Cloud에 공개 데모를 배포했다([enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/)). 현재 증빙 우선순위는 실제 추적 검증, 폭넓은 답변 품질 측정, 검색·생성 실패와 개선 이유 설명이다. 과거 배포 운영 제안은 이력 또는 선택 사항으로 보존하며 기업용 문서 관리와 접근 권한은 구현하지 않았다.

소스 코드, 기존 Phase 문서, 저장된 평가 산출물, 로컬 Python 환경을 확인했다. 이번 재검증은 오프라인 검사다. 실제 Claude 답변과 브라우저 스크린샷은 2026-10-14의 기존 증빙이며, 이번 점검에서 해당 호출을 반복하거나 원격 GitHub·Cloud 배포 상태를 확인하지 않았다.

| 영역 | 구현 내용과 근거 | 상태 |
| --- | --- | --- |
| Phase 1: 문서 처리 | `ingest.py`의 실제 페이지 추출·고정 청크 ID·평가 데이터 제외. PDF 4개, 13페이지, 청크 22개 | 로컬 완료 |
| Phase 2: 검색 | `embeddings.py`, `index_store.py`, `rag.py`의 로컬 E5·Chroma 영구 저장·무결성 확인·호환 인덱스 재사용·명시적 재생성 | 로컬 완료, 실제 설정 k=3 |
| Phase 3: 답변 | `RAGAssistant.answer()`의 검색 1회·최대 Claude 호출 1회. `grounding.py`의 JSON·출처 ID·원문 발췌 검증과 근거 부족 시 보류 | 로컬 완료, 답변 내용의 완전성은 개선 필요 |
| Phase 4: 화면 | `app.py`, `app_runtime.py`, `source_display.py`의 예시·세션 대화·인용·발췌·오류·응답시간·리소스 캐시·10회 제한 | 로컬 완료, 실제 브라우저 증빙 있음 |
| Phase 5: 평가 | 기존 10문항과 60문항 비교, 답변·AI 채점 각 120개, 지표 재현, 중간 저장 복구, 검토 내보내기 보호 | 구현 및 재현 완료 |
| Phase 5: 추적 | `tracing.py`의 검색·생성 구분과 추적 실패 격리. `eval/check_trace.py`의 실제 원격 실행 재조회 | 구현 완료, 실제 검증 대기 |
| Phase 5: 배포 | `deployment.py`, 사전 계산 벡터 번들, Streamlit 설정, 배포 안내 | 2026-10-16 배포([공개 URL](https://enterprise-rag-demo-project.streamlit.app/)), 사용자 시크릿 창 확인만 완료. Cloud 재시작·시작 시간·메모리 미검증 |
| 사람 검토 | 의심 답변 26건·AI 통과 표본 8건, 총 23개 질문에 대한 검토 목록 34건 | 후속 작업으로 보류, AI 점수와 구분 |

구현 상세: [Phase 1](Phase1_Foundation.md), [Phase 2](Phase2_IndexingAndRetrieval.md), [Phase 3](Phase3_GroundedAnswers.md), [Phase 4](Phase4_StreamlitInterface.md), [Phase 5](Phase5_EvaluationAndDeployment.md).

## 최초 Phase 5 재검증 결과 — 2026-10-16 (과거 기록)

| 검사 | 확인 결과 |
| --- | --- |
| 기존 전체 테스트 | **243개 통과, 60.40초**, 종료 코드 0 |
| Python·의존성 | Python 3.12.10, `pip check` 충돌 없음 |
| 메모리 내 문서 전처리 | 문서 4개, 텍스트 페이지 13개, 제외 페이지 0개, 청크 22개 |
| 저장 평가 산출물 검증 | 질문 60개, 답변 120개, 검토 120개. 해당 저장 실행의 RAG 오류·답변 누락·채점 오류 및 누락 없음 |
| 배포 번들 | 청크 22개 검증 통과, 이전 검증과 같은 번들 체크섬 |
| 로컬 적용 설정 | 청크 800자, 중복 120자, k=3. Claude 키 존재 여부만 확인했으며 현재 API 접속은 미검증 |
| 실제 추적 준비 | 추적 꺼짐, LangSmith 키 없음, 로컬 `data/trace_check.json` 없음 |
| CI | 프로젝트에 `.github/workflows/` 디렉터리 없음 |

[당일 검증 기록](../eval/results/phase5_v2_20261014/verification_20261016.json)에 근거를 남겼다. 테스트 통과는 프로그램 동작 검증이며 답변 정답률을 뜻하지 않는다. 이번 검사에서 새 모델 답변이나 AI 채점을 생성하지 않았다.

## 평가 결과로 판단한 개선 지점

[저장된 확대 평가](../eval/results/phase5_v2_20261014/report.md)는 개발용 검색 결과로 선택한 B(800/120/k=5)를 A(800/120/k=3)와 비교했다.

| 지표 | A: 현재 기본값 | B: 평가한 대안 |
| --- | --- | --- |
| 개발용 AI 정답률 | 35/40, 87.5% | 39/40, 97.5% |
| 최종 확인용 AI 정답률 | 13/20, 65.0% | 15/20, 75.0% |
| 최종 확인용의 답변 가능한 질문 정답률 | 9/16, 56.25% | 11/16, 68.75% |
| 최종 확인용 필수 원문 전체 포함률 | 9/16, 56.25% | 11/16, 68.75% |
| 최종 확인용 다중 문서 페이지 Coverage | 1/6 | 3/6 |
| 최종 확인용 답변 불가 질문 보류 | 4/4 | 4/4 |
| 개발용 평균 / p95 RAG 시간 | 3.00 / 4.35초 | 3.44 / 6.09초 |

같은 모델이 생성과 채점을 수행한 소규모 합성 데이터의 단일 실행 결과다. 기존 10문항의 90%만을 현재 품질의 대표 수치로 제시하면 부족하다. B는 두 구간에서 총 6개 답변이 개선됐고 관측된 악화는 없지만, 개발용 생성 입력 토큰이 133,049개에서 185,176개로 약 39% 늘었다. 토큰 사용량이며 금액으로 환산한 비용이나 B가 항상 느리다는 증거는 아니다.

근거를 바탕으로 다음 세 가지를 우선한다.

1. **필수 조항을 함께 검색하기.** q31/B는 검수 등록 기한을 찾지 못해 불완전한 문맥에서 답변을 보류했다. 전체 RAG의 검색 실패이며 보류 원칙을 약화할 이유는 아니다. k=5에서도 최종 다중 문서 검색은 부족하다.
2. **조건과 시점을 빠뜨리지 않기.** q08/A는 채점 기준 충족 해석에 차이가 있고, q54/B는 긴급 상황에서의 사전 확인 조건을 빠뜨렸다. 원문 일치는 출처를 검증하지만 질문의 모든 요구사항 충족을 보장하지 않는다.
3. **모델 실패와 평가의 한계를 구분하기.** 일부 AI 설명은 문서 전체에 답이 있다는 이유로 검색 문맥에서 타당한 보류까지 “잘못된 보류”로 표현한다. 다음 분석에서는 검색 근거 부족·생성 누락·채점 해석 문제를 나누고 기존 판정은 과거 증빙으로 보존한다.

`config.load_settings()`와 동적 출처 스키마는 `RAG_TOP_K`를 지원한다. k는 `index_signature()`에 포함되지 않아 k만 바꾸면 인덱스를 재생성할 필요가 없다. 현재 설정 예시 2개에는 `RAG_TOP_K=3`이 명시되어 있다. Phase 6에서 선택형 `RAG_RETRIEVAL_MODE=pages`와 문맥 한도를 추가했고 pages/k=5를 후보로 선택했다. 해당 후보의 게시는 완료된 로컬 구현과 별도다.

## 앞으로 개발할 순서

최신 [Phase 6 결과와 한계](Phase6_RetrievalAndAnswerQuality.md#검증-진단과-근거-선택)가 과거 배포 제안보다 우선한다. 위 최초 점검은 과거 기록이며, 당시의 키·실제 추적 미확인 상태는 현재와 다르다.

| 우선순위 | 남은 작업 | 이유와 현재 상태 |
| --- | --- | --- |
| 로컬 완료 | 검증 규칙·발생 위치의 안전한 기록 | 실행기·평가기에서 규칙·위치와 응답 길이·해시를 보존한다. 엄격한 검사는 유지하며 원래 상세를 기록하지 않은 과거 4건의 원인은 알 수 없음으로 남긴다. |
| 로컬 완료 | 최종 근거 선택 개선 | 마지막 한 칸만 제한적으로 바꿔 q51의 후보 9위 페이지를 확보한다. 같은 후보의 오프라인 근거 확보는 47/48→48/48이며 전체 근거 확보 악화는 없다. 새 답변 정확도는 미측정이다. |
| 사용자 결정으로 보류 | 실패한 AI 채점 87건 복구 | API 잔액 부족을 확인했고 지금은 충전하지 않기로 했다. 답변과 오프라인 복구 계획을 저장했으므로 이후 채점만 이어갈 수 있다. 보류 중에는 추가 모델 호출을 하지 않는다. |
| 사람 검토 보류 | 기존 검토 목록 34건 보존 | AI 판정은 사람 검증이 아니다. 요청 시 재개하고 기존 점수·메모는 유지한다. |
| 후속 품질 증빙 | 새 독립 질문을 먼저 준비한 뒤 정확도 평가 | 현재 60개는 모두 이미 확인한 문제다. 구현 변경·평가 전에 질문, 참고 근거, 채점 기준을 고정한다. |
| 선택적 보조 작업 | Cloud 자원 검사·CI·SDK 유지보수 | 이후 도움이 되지만 현재 RAG 시연의 필수 요건은 아니다. |
| 명시적 보류·제외 | Phase 7 사용성 / 동시 접속 검사 | 사용성은 보류, 동시 접속 검사는 목표 범위 밖이다. |

## 바로 이어서 할 작업과 결정 사항

**로컬 완료:** 추적 계층·토큰 기록 수정, pages/5/6000의 실제 원격 대조, 쌍별 답변 120회 시도 기록, 오프라인 산출물 검증, 채점 복구 준비, 검증 진단, 마지막 페이지 선택, 테스트 347개 통과. 과거 답변 비교의 필수 근거 확보는 청크 37/48·페이지 47/48이며 최신 검색만 비교한 선택 검사는 48/48이다. 과거 실행에서 검증을 통과한 응답은 59/60·57/60이다. AI 채점은 가능한 응답 중 15/59·14/57만 완료했다. 원본의 확인된 통과 개수 14/60을 정확도 비율로 해석하지 않는다.

**최신 사용자 결정:** 지금은 충전하지 않고 잔여 AI 채점 87건을 보류한다. 복구 준비에는 API를 호출하지 않았다. 사용자가 채점을 재개하기 전에는 `run`을 실행하지 않는다. [준비된 계획](../eval/results/phase6_review_recovery_selection_20261016/plan.json)은 저장된 성공 답변 중 채점 실패 건만 대상으로 삼는다. 소스 해시가 바뀌어 향후 실행에는 새 계획을 사용하며 이전 계획도 보존했다. 나중에 해당 채점을 완료해도 새 선택 방식이 아닌 이전 답변을 평가한다. 복구 중 제공업체 오류가 다시 발생하면 첫 오류에서 멈추고 기존 결과를 보존한다.

사용자가 보고한 Cloud pages/5/6000 설정·Reboot와 검증된 로컬 실행을 구분한다. 이번 개정은 완료한 후속 변경을 별도 enterprise-rag 체크아웃에서 GitHub에 게시하도록 묶었다. 개발·검증은 로컬에서 수행했으며 이번 개정의 Cloud 동작은 아직 별도로 검증하지 않았다. 답변 프롬프트는 유지했다. 새 선택 규칙은 알려진 사례로 확인했으므로 새 독립 질문 준비가 다음 우선순위다. Phase 6 증빙으로 측정한 효과와 실패를 설명하고 사람 검토·독립 평가의 한계를 유지한다.

## 로컬 검증 재현

프로젝트 루트의 기존 환경에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.selection verify --output-dir eval/results/phase6_selection_20261016
.\.venv\Scripts\python.exe -X utf8 deployment.py check
```

Cloud 설정 시 저장소·브랜치·진입 파일·Python·서버 시크릿은 [Streamlit 공식 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)를 따른다. 추적 설정과 계층 구조는 [LangSmith 공식 계측 안내](https://docs.langchain.com/langsmith/annotate-code)를 참고한다. 2026-10-16 확인한 자료이며 이 앱의 배포 완료 증빙은 아니다. 프로젝트별 인수 절차는 [DEPLOYMENT.md](../DEPLOYMENT.md)에 있다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-16 | 코드 기반 현황 점검, 오프라인 검증 갱신, 단계별 개발 계획 신규 작성. 실행 코드·모델 평가·배포·사람 채점은 변경하지 않음. 별도 dev-log 미설치로 여기에 이력 기록. |
| 2026-10-16 | Streamlit Community Cloud 배포와 공개 URL 기록, 저장소 공개 전환. 문서만 수정했으며 실행 코드·설정·평가는 변경하지 않음. 정식 Cloud 인수 검사와 실제 Trace는 대기. |
| 2026-10-16 | Phase 5 검사 보류 요청을 반영하고 Phase 6 로컬 완료·증빙 연결. 설정 예시에 RAG_TOP_K가 없다는 오래된 설명 수정. Cloud에는 게시하지 않음. |
| 2026-10-16 | b89ed76 코드 푸시와 Phase 6 pages/5/6000 활성화 우선 결정을 기록했다. Phase 7 사용성을 명시적으로 보류하고 그 외 검사는 대기 상태를 유지했다. 세션에 Cloud Settings 접근 연결이 없어 활성화 완료로 표시하지 않았다. 문서만 갱신했으며 별도 dev-log는 미설치로 생략했다. |
| 2026-10-16 | 사용자의 설정·Reboot 완료 보고를 기록했다. 목표를 RAG 이해·측정한 정확도·정교한 근거 처리·개선 설명으로 재정렬하고 동시 접속 검사 제외·사용성 보류를 반영했다. 추적·평가는 다음 제안이며 새 실행 완료로 표시하지 않았다. 별도 dev-log 미설치로 문서 이력에 기록했다. |
| 2026-10-16 | 실제 LangSmith·테스트 305개·근거 확보 37/48 대비 47/48·AI 채점 미완료·사용자의 충전 보류·오프라인 복구 준비를 기록했다. 실패 상세·근거 선택·후속 독립 평가를 우선하고 보류 후 추가 호출이나 푸시는 하지 않았다. 별도 dev-log 미설치로 여기에 기록. |
| 2026-10-16 | 검증 진단·마지막 페이지 선택을 오프라인으로 완료. 테스트 347개·근거 확보 48/48·전체 근거 확보 악화 없음. 현재 코드의 87건 복구 계획만 준비하고 원본·유료 채점 보류를 유지했다. 다음 우선순위는 새 독립 질문 준비다. |
