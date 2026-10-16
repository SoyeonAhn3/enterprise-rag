# Development Status and Roadmap

**Reviewed**: 2026-10-16 (Asia/Seoul)\
**Current milestone**: Phases 1–4 verified locally; Phase 5 in progress.\
**Planning assumption**: Finish the existing public portfolio MVP first. Later product expansion is proposed, not implemented or committed.

## Where development stands

The local application already performs the complete PDF → search → grounded Korean answer → source display flow. The remaining MVP work is deployment, real remote trace verification, and release evidence. It is a working fixed-document demonstration; enterprise document administration and access control are not implemented.

This review checked source code, existing Phase reports, saved evaluation artifacts, and the local Python environment. The fresh checks below are offline. Live Claude answers and browser screenshots are historical evidence from 2026-10-14; this audit did not repeat those calls or inspect the remote GitHub/Cloud deployment.

| Area | Implemented behavior and evidence | Status |
| --- | --- | --- |
| Phase 1: documents | `ingest.py` extracts physical pages, creates stable chunk IDs, and excludes evaluation data; 4 PDFs, 13 pages, 22 chunks | Locally complete |
| Phase 2: retrieval | `embeddings.py`, `index_store.py`, `rag.py`: local E5 embeddings, persistent Chroma, integrity checks, compatible reuse, explicit rebuild | Locally complete; effective k=3 |
| Phase 3: answers | `RAGAssistant.answer()` retrieves once and makes at most one Claude call; `grounding.py` validates JSON, source IDs, and original quotes; insufficient evidence causes abstention | Locally complete; semantic completeness remains a quality limitation |
| Phase 4: interface | `app.py`, `app_runtime.py`, `source_display.py`: examples, session chat, citations, excerpts, errors, latency, cached resources, ten-attempt limit | Locally complete; real browser evidence already saved |
| Phase 5: evaluation | Original ten-question baseline plus 60-question comparison, 120 answers/AI grades, reproducible metrics, checkpoint recovery, protected review exports | Implemented and reproduced |
| Phase 5: tracing | `tracing.py` separates retrieval/generation and isolates tracing failures; `eval/check_trace.py` can read back the remote run tree | Implemented; real verification pending |
| Phase 5: deployment | `deployment.py`, portable vector bundle, Streamlit settings, deployment guide | Locally validated; public URL and Cloud restart unverified |
| Human review | 34 queue entries: 26 flagged answers and 8 sampled passes across 23 questions | Deferred; AI scores are not human validation |

Phase implementation records: [1](Phase1_Foundation.md), [2](Phase2_IndexingAndRetrieval.md), [3](Phase3_GroundedAnswers.md), [4](Phase4_StreamlitInterface.md), [5](Phase5_EvaluationAndDeployment.md).

## Fresh verification on 2026-10-16

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

`RAG_TOP_K` is already supported by `config.load_settings()` and the dynamic source schema; k=5 does not require a new retrieval engine. Changing only k does not require rebuilding the index because k is outside `index_signature()`. The environment and server-secret examples currently omit this option. Candidate promotion still needs an explicit release decision and regression verification.

## Development order

Only the current Phase 5 is expanded into executable tasks, in the [Phase 5 remaining-work table](Phase5_EvaluationAndDeployment.md#remaining-work-after-the-2026-10-16-audit). Later phases below are proposed milestones whose detailed scope should be set when they start.

| Priority / milestone | Development work | Completion evidence / dependency | Initial effort estimate |
| --- | --- | --- | --- |
| P0 — Finish Phase 5 | Freeze a reproducible release, reconcile configuration/docs, verify Linux startup, connect real tracing, deploy the public demo, record evidence | Public visitor can ask q01/q07/q09 and inspect sources without a key; restart works; real retrieval/generation trace verified | 2–3 working days after account/key access is ready |
| P1 — Proposed Phase 6: retrieval and answer quality | Evaluate promotion of k=5 first; then improve clause/section chunk boundaries and bounded context assembly where evidence still goes missing; refine condition-preserving answers and failure classification | Compare complete evidence, multi-document coverage, answerable correctness, abstention, tokens, and latency against a frozen baseline; preserve one retrieval / at most one generation | 2–4 working days; new scope set after Phase 5 |
| P2 — Proposed Phase 7: demo usability and operation | Read-only quality-results view, easier original-PDF/page inspection, clearer document coverage, and small concurrent-session checks | UI uses saved results without triggering evaluation calls; citations remain accurate; startup and request waiting are measured separately | 1–2 working days; depends on a stable deployed configuration |
| P3 — Optional enterprise expansion | First define users, document confidentiality, permissions, storage, and retention; then consider upload/versioning, incremental indexing, authentication, authorization, and operational audit records | Requirements and deployment design agreed before accepting non-public documents; authorization enforced before retrieval and in source access | Not estimated; outside the present MVP |

These estimates are planning judgments for one developer, not measured durations or delivery commitments. Account setup, human-review scheduling, and platform incidents are excluded. Phases 6–7 are new proposals; their numbering does not change the completion status of Phases 1–5.

Hybrid search, reranking, OCR, agentic retrieval, and a separate backend remain outside the existing MVP. Consider them only after simpler retrieval changes have measured results and a new scope warrants them. More automated grading infrastructure is also lower priority than finishing the already-built demo.

## Immediate work sequence and decisions

1. Freeze the release snapshot and keep k=3 for the existing MVP release unless a separate quality-change decision is recorded. Align current instructions and configuration examples, then run a fresh-environment check. This workspace belongs to a parent Git repository; use the established separate project checkout to identify the release commit. This audit did not verify remote synchronization.
2. Verify Linux/Cloud startup, initial model download, vector import, and restart. Add a small CI workflow for existing offline checks; its file path in the Phase 5 plan is a proposal, not an existing file.
3. Configure the operator's LangSmith key and run the existing remote checker. Cloud preparation can proceed while that credential is unavailable; missing tracing must continue to leave ordinary answers usable.
4. Deploy, verify the public visitor flow and provider usage controls, then update the actual URL, screenshots, configuration, and trace evidence together. A per-session request limit is already implemented; no application-wide spending cap exists in the code.

The existing user decision recorded in Phase 5 defers full human grading. Keep that decision: the 34-entry queue stays pending and clearly labeled. When review resumes, prioritize q08/A, q31/B, q49/A, q54/B, and the saved pass sample; do not overwrite historical AI grades or human CSV notes.

For Phase 6, the v2 final split has now been inspected and must not be reused as an unseen test for tuning based on those failures. Preserve v2 results and prepare a separately versioned holdout before the next quality experiment. Any new dataset, runner extension, or result directory is future work. Freeze selection rules and promotion criteria before the run; do not invent an accuracy target after seeing results.

The current shared `AppResources` lock serializes requests. Measure browser waiting and startup separately from stored RAG latency before claiming multi-user responsiveness. Larger-scale serving changes need observed load evidence.

## Reproducible local checks

Run from the project root using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 deployment.py check
```

For future Cloud setup, select the repository, branch, entrypoint, Python version, and server secrets using [Streamlit's official deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). LangSmith's [official instrumentation guide](https://docs.langchain.com/langsmith/annotate-code) explains trace configuration and hierarchy. These references were checked on 2026-10-16; neither establishes that this app has been deployed. Project-specific acceptance steps remain in [DEPLOYMENT.md](../DEPLOYMENT.md).

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-16 | Created a source-backed status audit, refreshed offline evidence, and proposed a staged roadmap. No runtime changes, new model evaluation, deployment, or human grading. Separate dev-log unavailable; history recorded here. |

---

# 개발 현황 및 향후 개발 계획

**점검일**: 2026-10-16 (한국 시간)\
**현재 단계**: Phase 1~4 로컬 검증 완료, Phase 5 진행 중.\
**계획 전제**: 기존 공개 포트폴리오 MVP를 먼저 마무리한다. 이후 제품 확장은 제안이며 구현·착수가 확정된 상태가 아니다.

## 현재 어디까지 개발했는가

로컬에서는 PDF → 검색 → 근거 기반 한국어 답변 → 출처 표시의 전체 흐름이 동작한다. 남은 MVP 작업은 배포, 실제 원격 Trace 검증, 제출 증빙 정리다. 고정 문서 데모로는 동작하지만 기업용 문서 관리와 접근 권한은 구현하지 않았다.

소스 코드, 기존 Phase 문서, 저장된 평가 산출물, 로컬 Python 환경을 확인했다. 이번 재검증은 오프라인 검사다. 실제 Claude 답변과 브라우저 스크린샷은 2026-10-14의 기존 증빙이며, 이번 점검에서 해당 호출을 반복하거나 원격 GitHub·Cloud 배포 상태를 확인하지 않았다.

| 영역 | 구현 내용과 근거 | 상태 |
| --- | --- | --- |
| Phase 1: 문서 처리 | `ingest.py`의 실제 페이지 추출·고정 청크 ID·평가 데이터 제외. PDF 4개, 13페이지, 청크 22개 | 로컬 완료 |
| Phase 2: 검색 | `embeddings.py`, `index_store.py`, `rag.py`의 로컬 E5·Chroma 영구 저장·무결성 확인·호환 인덱스 재사용·명시적 재생성 | 로컬 완료, 실제 설정 k=3 |
| Phase 3: 답변 | `RAGAssistant.answer()`의 검색 1회·최대 Claude 호출 1회. `grounding.py`의 JSON·출처 ID·원문 발췌 검증과 근거 부족 시 보류 | 로컬 완료, 답변 내용의 완전성은 개선 필요 |
| Phase 4: 화면 | `app.py`, `app_runtime.py`, `source_display.py`의 예시·세션 대화·인용·발췌·오류·응답시간·리소스 캐시·10회 제한 | 로컬 완료, 실제 브라우저 증빙 있음 |
| Phase 5: 평가 | 기존 10문항과 60문항 비교, 답변·AI 채점 각 120개, 지표 재현, 중간 저장 복구, 검토 내보내기 보호 | 구현 및 재현 완료 |
| Phase 5: 추적 | `tracing.py`의 검색·생성 구분과 추적 실패 격리. `eval/check_trace.py`의 실제 원격 실행 재조회 | 구현 완료, 실제 검증 대기 |
| Phase 5: 배포 | `deployment.py`, 사전 계산 벡터 번들, Streamlit 설정, 배포 안내 | 로컬 검증 완료, 공개 URL·Cloud 재시작 미검증 |
| 사람 검토 | 의심 답변 26건·AI 통과 표본 8건, 총 23개 질문에 대한 검토 목록 34건 | 후속 작업으로 보류, AI 점수와 구분 |

구현 상세: [Phase 1](Phase1_Foundation.md), [Phase 2](Phase2_IndexingAndRetrieval.md), [Phase 3](Phase3_GroundedAnswers.md), [Phase 4](Phase4_StreamlitInterface.md), [Phase 5](Phase5_EvaluationAndDeployment.md).

## 2026-10-16 실제 재검증 결과

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

`config.load_settings()`와 동적 출처 스키마가 이미 `RAG_TOP_K`를 지원하므로 k=5에 새 검색 엔진은 필요 없다. k는 `index_signature()`에 포함되지 않아 k만 바꾸면 인덱스도 재생성할 필요가 없다. 현재 환경·서버 시크릿 예시에는 해당 옵션이 빠져 있다. 실제 적용에는 명확한 배포 설정 결정과 회귀 확인이 필요하다.

## 앞으로 개발할 순서

현재 Phase 5만 [잔여 작업표](Phase5_EvaluationAndDeployment.md#remaining-work-after-the-2026-10-16-audit)에서 실행 가능한 Task로 상세화했다. 이후 단계는 착수할 때 상세 범위를 정할 제안이다.

| 우선순위·단계 | 개발 내용 | 완료 근거·선행 조건 | 초기 예상 작업량 |
| --- | --- | --- | --- |
| P0 — Phase 5 마무리 | 재현 가능한 배포본 확정, 설정·문서 정합성, Linux 시작 검증, 실제 추적 연결, 공개 배포, 증빙 기록 | 외부 방문자가 키 입력 없이 q01·q07·q09와 출처 확인. 재시작 정상. 실제 검색·생성 Trace 검증 | 계정·키 준비 후 2~3작업일 |
| P1 — 제안 Phase 6: 검색·답변 품질 | 우선 k=5 적용 검토. 남은 근거 누락에는 조항·섹션 단위 청크와 크기를 제한한 문맥 구성 개선. 조건을 보존하는 답변과 실패 분류 보완 | 고정 기준 대비 전체 근거·다중 문서·답변 가능 질문 정답률·보류·토큰·시간 비교. 검색 1회·최대 생성 1회 유지 | 2~4작업일, Phase 5 후 범위 확정 |
| P2 — 제안 Phase 7: 시연 사용성·운영 | 저장 평가 결과 조회, 원본 PDF·페이지 확인 개선, 문서 범위 안내, 소수 동시 세션 확인 | UI에서 평가 호출 없이 저장 결과 조회. 출처 정확성 유지. 시작 시간과 요청 대기 시간 별도 측정 | 1~2작업일, 안정된 공개 설정 선행 |
| P3 — 선택적 기업용 확장 | 사용자·문서 기밀성·권한·저장소·보존 기준부터 정의. 이후 업로드·버전·증분 인덱싱·인증·인가·운영 감사 기록 검토 | 비공개 문서 취급 전 요구사항·배포 설계 확정. 검색 전과 원문 접근에서 권한 적용 | 미산정, 현재 MVP 범위 밖 |

작업량은 개발자 1명 기준의 계획상 추정이며 실측이나 납기 약속이 아니다. 계정 준비, 사람 검토 일정, 플랫폼 장애 대기는 제외했다. Phase 6~7은 새 제안이며 Phase 1~5의 완료 상태를 바꾸지 않는다.

Hybrid Search, Reranker, OCR, 에이전트 검색, 별도 백엔드는 기존 MVP 범위 밖이다. 단순한 검색 개선을 측정한 뒤 새로운 범위가 필요할 때 검토한다. 자동 채점 시스템을 더 키우는 작업도 이미 만든 데모의 공개 완료보다 후순위다.

## 바로 이어서 할 작업과 결정 사항

1. 배포할 코드·설정 묶음을 확정한다. 별도의 품질 변경 결정을 기록하기 전에는 기존 MVP의 k=3을 유지한다. 실행 안내·설정 예시를 맞추고 새 환경을 검사한다. 현재 폴더는 상위 Git 저장소에 속하므로 기존에 사용한 분리된 프로젝트 체크아웃에서 배포 커밋을 식별한다. 이번 점검에서 원격 동기화는 확인하지 않았다.
2. Linux·Cloud 시작, 최초 모델 다운로드, 벡터 가져오기, 재시작을 검증한다. 기존 오프라인 검사를 실행하는 작은 CI 워크플로도 추가한다. Phase 5에 적은 워크플로 경로는 예정 파일이다.
3. 운영자 LangSmith 키를 설정하고 기존 원격 검증기를 실행한다. 키가 준비되지 않아도 Cloud 준비는 진행할 수 있으며, 추적 누락이 일반 답변을 막지 않는 동작을 유지한다.
4. 공개 배포 후 방문자 사용 흐름과 제공업체 사용량 제어를 확인한다. 실제 URL·스크린샷·설정·추적 증빙을 함께 갱신한다. 현재 코드는 세션별 요청 제한을 제공하며 앱 전체 비용 상한은 구현하지 않았다.

Phase 5에 기록된 기존 사용자 결정에 따라 전체 사람 채점은 계속 뒤로 미룬다. 검토 목록 34건은 대기로 명시한다. 검토를 재개하면 q08/A·q31/B·q49/A·q54/B와 저장된 통과 표본부터 확인하고, 과거 AI 채점과 사람이 작성한 CSV 메모는 덮어쓰지 않는다.

Phase 6에서는 이미 확인한 v2 최종 구간을 해당 실패에 맞춰 개선한 뒤 다시 미관측 시험으로 취급하지 않는다. v2 결과를 보존하고 다음 품질 실험 전에 별도 버전의 최종 확인 데이터를 준비한다. 새 데이터셋·실행기 확장·결과 폴더는 향후 작업이다. 선택 규칙·적용 기준은 실행 전에 정하며, 결과를 본 뒤 정확도 목표를 만들어 붙이지 않는다.

현재 `AppResources`의 공유 잠금은 요청을 순서대로 처리한다. 다중 사용자 응답성을 주장하기 전에 브라우저 대기·시작 시간과 저장된 RAG 시간을 구분해 측정한다. 더 큰 규모의 서빙 변경은 실제 부하 근거에 따라 판단한다.

## 로컬 검증 재현

프로젝트 루트의 기존 환경에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 deployment.py check
```

Cloud 설정 시 저장소·브랜치·진입 파일·Python·서버 시크릿은 [Streamlit 공식 배포 안내](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)를 따른다. 추적 설정과 계층 구조는 [LangSmith 공식 계측 안내](https://docs.langchain.com/langsmith/annotate-code)를 참고한다. 2026-10-16 확인한 자료이며 이 앱의 배포 완료 증빙은 아니다. 프로젝트별 인수 절차는 [DEPLOYMENT.md](../DEPLOYMENT.md)에 있다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-16 | 코드 기반 현황 점검, 오프라인 검증 갱신, 단계별 개발 계획 신규 작성. 실행 코드·모델 평가·배포·사람 채점은 변경하지 않음. 별도 dev-log 미설치로 여기에 이력 기록. |
