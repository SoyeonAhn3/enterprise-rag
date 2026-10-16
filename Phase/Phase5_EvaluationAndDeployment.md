# Phase 5 — Evaluation, Tracing, and Deployment `🚧 In Progress`

> Demonstrate the application with measured results, a real trace, and a working public URL.

**Status**: 🚧 Ten-question baseline and expanded 60-question AI evaluation completed on 2026-10-14; reporting hardened on 2026-10-15 and offline checks passed again on 2026-10-16. The public demo was deployed to Streamlit Community Cloud on 2026-10-16. Human review is deferred; a real LangSmith trace and formal Cloud acceptance checks remain pending.\
**Prerequisites**: [Phase 4](Phase4_StreamlitInterface.md) works locally; API access, a LangSmith project, and GitHub/Streamlit deployment access are available.\
**Planned technology**: Python evaluation runner, JSON results, reference-based AI grading and a deferred human-review queue, LangSmith, Streamlit Community Cloud.

## Overview

Preserve the original ten-question baseline, expand evaluation under the protocol below, inspect retrieval and generation traces, and deploy the verified corpus and settings. AI grading and human verification are reported separately. Live tracing and public deployment are outside the current evaluation execution.

The missing Phase 4 interface was implemented and verified locally first. The user selected `https://github.com/SoyeonAhn3/enterprise-rag.git` and confirmed the Streamlit/GitHub account connection. Claude credentials work locally; LangSmith credentials are not configured. On 2026-10-16 `main` was deployed to Streamlit Community Cloud at [enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/), and the repository was made public. The owner confirmed the app works in a private browser window, and an anonymous request reached the app without sign-in.

## Tasks and current evidence

| Deliverable | Completion criterion | Verification approach |
| --- | --- | --- |
| ✅ Evaluation runner | Ten results retain retrieval, answers, settings, errors, and timing; metrics are reproducible | Real ten-question baseline completed; checkpoint/error/denominator/integrity tests passed |
| 🚧 Review | All ten answers are checked against criteria with evidence notes; identify the reviewer accurately | Agent review recorded 9/10 correctness and 10/10 grounding; blank report-bound human review remains pending |
| ✅ Expanded AI evaluation | Frozen 60-question dataset, development-only selection, paired answers and verified judge notes | Twelve-case pilot; four retrieval settings; B (800/120/k=5) selected; 120 saved answers and 120 AI grades; 34 human-review entries |
| ✅ Offline reproduction | Validate the artifact chain and expose failed/missing answers in exports | Read-only `benchmark verify`; recomputed metrics/queue; regression coverage for mixed runs, invalid grades, missing answers, and human CSV notes |
| ✅ LangSmith | Separate retrieval/generation spans; tracing failure does not break answers; verify one real remote tree | ✅ Local-to-remote pages/5/6000 verified 2026-10-16; see Phase 6 follow-up. Cloud tracing remains separate. |
| 🚧 Public deployment | Public key-free visitor flow and index reload after restart | Local real browser and portable index import/reload passed. Deployed to Community Cloud on 2026-10-16; owner's private-window check passed. Formal q01/q07/q09, restart, and resource checks pending |
| 🚧 Portfolio evidence | Actual measurements, failure analysis, screenshots, trace/public links | Bilingual docs, local screenshots, and saved JSON ready; live URL recorded on 2026-10-16. Public screenshots and trace evidence remain absent |

Implemented [eval/evaluate.py](../eval/evaluate.py), [tracing.py](../tracing.py), [eval/check_trace.py](../eval/check_trace.py), [deployment.py](../deployment.py), the portable index bundle, Streamlit settings/interface, tests, and [deployment instructions](../DEPLOYMENT.md). Existing packages were preserved when Streamlit was installed; `pip check` found no broken requirements. `.env` gained only missing optional tracing/session settings, preserving the Claude key.

The original Phase 5 audit passed **243 tests in 60.40 seconds** on 2026-10-16. The later [Phase 6 follow-up](Phase6_RetrievalAndAnswerQuality.md#follow-up-results-and-remaining-work) passed 305 tests. Dependency checks, saved benchmark verification, and the 22-chunk deployment bundle also passed. That Phase 5 audit generated no new model answers or AI grades. See the [2026-10-16 verification record](../eval/results/phase5_v2_20261014/verification_20261016.json). The [2026-10-15 record](../eval/results/phase5_v2_20261014/verification_20261015.json) preserves the earlier 20.25-second run and 20 added reporting regressions. Automated tests remain separate from live model evaluation and browser checks.

## Remaining work after the 2026-10-16 audit

The [development status and roadmap](DevelopmentStatusAndRoadmap.md) consolidates implementation evidence and proposed later milestones. Finish the existing public MVP first. The following tasks detail only the current phase; CI and configuration-document cleanup are proposed release work, not missing implementations in Phases 1–4.

| Task / priority | Work and affected files | Acceptance criterion | Verification | Status |
| --- | --- | --- | --- | --- |
| 5.R1 / P0 | Audit source, corpus, effective settings, saved evaluation, dependencies, and tests | Current state has dated, reproducible evidence without generating new answers | Existing full suite, `pip check`, `benchmark verify`, `deployment.py check`; record linked above | ✅ Complete |
| 5.R2 / P0 | Identify the release snapshot in the separate project checkout; align `.env.example`, `.streamlit/secrets.toml.example`, README, and the original plan with the current Claude/local-E5/vector-bundle implementation; document `RAG_TOP_K=3` explicitly | One documented release configuration; obsolete OpenAI/native-index examples cannot be mistaken for current instructions; quality changes are separately identified | Compare release files with the audited workspace; inspect loaded non-secret settings and deployment bundle compatibility | 🟡 Partly done (2026-10-16): release pushed from the separate checkout; example files document `RAG_TOP_K=3` and load correctly. The original plan still contains OpenAI-era text |
| 5.R3 / P0 startup, P1 CI | Validate a fresh Linux/Python 3.12 environment and startup; add a small offline CI workflow at `.github/workflows/ci.yml` (proposed file) | Dependencies and existing checks pass on Linux; first vector import and restart work without document embedding; actual query-model startup is separately recorded | Fresh install, four offline commands in the roadmap, cache-download/restart smoke check; record startup time and memory instead of assuming capacity | 🔲 Planned |
| 5.R4 / P0 | Supply operator LangSmith settings and run existing `eval.check_trace` | Remote root and completed retrieval/generation child runs match the observed answer; failure isolation remains intact | One live generation and remote read-back; local `data/trace_check.json`; existing failure-isolation tests | ✅ Local-to-remote pages/5/6000 verified 2026-10-16; see Phase 6 follow-up. Cloud tracing remains separate. |
| 5.R5 / P0 | Deploy `app.py` from the identified release to Community Cloud; configure server secrets and provider usage controls | Fresh visitor gets q01/q07 answers with real sources and q09 abstention without entering a key; refresh/restart works; usage-control settings are recorded | Private-browser checks, public URL, startup/restart logs, screenshots; inspect waiting with two sessions because shared resources serialize requests | 🟡 Deployed 2026-10-16 ([public URL](https://enterprise-rag-demo-project.streamlit.app/)); owner's private-window check only. Formal q01/q07/q09, restart, usage-control, and two-session checks not recorded |
| 5.R6 / P0 | Reconcile `README.md`, `README_ko.md`, `DEPLOYMENT.md`, and this report with the deployed release | Actual URL, release configuration, trace evidence, split-specific AI scores, and remaining limitations agree; no human-verification claim | Follow the public link and evidence from a fresh session; compare published settings/results to the release snapshot | 🟡 URL recorded in both READMEs, DEPLOYMENT.md, and this report; trace evidence depends on 5.R4 |

Suggested sequence: **5.R2 → 5.R3 startup → 5.R5 → 5.R6**; complete 5.R4 as soon as its credential is available and finish it before closing the phase. CI can be prepared alongside startup checks. Initial remaining effort is **2–3 working days for one developer**, excluding access/setup delays and platform failures; this is an estimate, not a delivery promise. The operator supplies server/account configuration; the developer performs implementation, verification, and evidence updates.

Keep k=3 for the existing MVP release unless a separate quality-change decision is recorded. k=5 is already supported and evaluated; the proposed Phase 6 will consider promotion before introducing more search machinery. Do not repeat the full 120-answer evaluation merely to document current status.

Human review remains deferred under the existing recorded user decision. Preserve the 34-entry queue and distinguish AI scores from human judgments; selective review can resume later. It is not silently converted into an additional deployment prerequisite. This phase still cannot be marked complete without verified public operation and a real trace. The 2026-10-16 audit itself did not access the remote repository, deploy, or perform a live model/browser check; the deployment followed later that day.

## Expanded evaluation protocol — agreed before execution (2026-10-14)

This evaluation uses AI review first. Full human grading is deferred at the user's request. The review queue retains questionable answers, exact sentences, missing requirements, source passages, and reasons; AI-approved answers are not human-verified results. No production configuration is changed by an experiment.

1. Freeze 60 document-grounded questions: 40 development questions (20 single-document, 12 multi-document, 8 unanswerable) and 20 final-check questions (10/6/4). The original ten belong to development. Keep paraphrases in the same split. Shared rules in this small synthetic corpus limit independence; the final split is a held-out configuration check, not an external benchmark.
2. Verify reference quotes against PDF pages before any model calls. Required evidence groups must cover required answer facts, including the general legal-review rule for q08. Preserve the original ten-question dataset and results; changes belong to a separately versioned dataset. References, criteria, and final-check answers never enter the RAG generation prompt or index.
3. Pilot the AI reviewer on the ten saved baseline answers, including the known q08 omission, and controlled wrong/unsupported examples. Freeze the reviewer prompt before the expanded run. The reviewer receives the question, criteria, reference passages, retrieved chunks, and generated answer in a separate call. The same configured Claude model may be used; this is not an independent human or independent-model assessment.
4. Compare retrieval on development questions only: A = 800 characters / 120 overlap / k=3; B = 800/120/5; C = 500/120/3; D = 800/0/3. Use separate index folders and the same PDFs/E5 model. Rank alternatives by all-required-quote coverage, then evidence-group recall, then page hit, then lower k, then configuration ID. Freeze one alternative before answer generation or final-check inspection.
5. Run A and the selected alternative on the same 40 development and then 20 final-check questions. Interleave configuration order by question. Keep the model, answer prompt, rubric, and documents fixed. Record every attempted answer and judge call, including errors and token usage; no automatic retries or silent removal of failures. This is one run per question/configuration, not a statistical significance claim.
6. Publish separate development/final metrics, paired outcomes, and a human-review queue. Human review remains a later task: inspect flagged answers and a reproducible sample of AI passes. Live LangSmith and public deployment remain separate pending checks.

| Criterion | Rule and reported denominator |
| --- | --- |
| Retrieval Hit@k | At least one allowed evidence page; answerable questions only. Report k explicitly. |
| Complete evidence / group recall | All required quote groups covered, plus fraction of individual groups covered; whitespace-only quote matching. Empty groups never count as successful retrieval. |
| AI correctness and completeness | All required facts correct, no contradictory conditions, and correct abstention when the corpus cannot answer. Score both all questions and answerable questions; missing/failed answers remain in denominators. |
| AI grounding | Every generated factual claim supported by retrieved text. A grounded but incomplete answer can still be incorrect. Report substantive answers separately from abstentions. |
| Review flags | Missing conditions, unsupported claims, wrong boundary/AND/OR/timing, unjustified abstention, conflicting evidence, or ambiguous rubric. Output exact answer span when present, criterion IDs, source quotes, and reason; omissions have an empty span and an explicit missing fact. |
| Errors and latency | Separate RAG errors, judge errors, and abstentions. Report successful mean/p50/p95 and attempted count; exclude initialization and judge latency from RAG latency. Record API token counts without inventing monetary costs. |

**Implementation/execution status:** completed on 2026-10-14 and verified offline on 2026-10-15. Existing ten-question scores below remain historical evidence under their original rubric.

## Expanded results and offline verification

The [expanded report](../eval/results/phase5_v2_20261014/report.md) and [metrics](../eval/results/phase5_v2_20261014/metrics.json) record 60 questions, 120 saved answers, and 120 AI grades. A uses 800/120/k=3; B uses 800/120/k=5. The development-only comparison selected B before final evaluation; the application still defaults to k=3.

| Split | A AI correctness | B AI correctness | A / B successful mean latency |
| --- | --- | --- | --- |
| Development, 40 questions | 35/40 (87.5%) | 39/40 (97.5%) | 3.00 / 3.44 seconds |
| Final check, 20 questions | 13/20 (65.0%) | 15/20 (75.0%) | 3.05 / 2.88 seconds |

Generation and grading used the same Claude model in separate calls. These are AI scores, not independent human judgments. The [review queue](../eval/results/phase5_v2_20261014/review_queue.csv) contains 26 flagged answers and 8 sampled passes across 23 questions. q08/A illustrates uncertain grading of omitted general conditions; q31/B abstains because retrieval missed a required deadline. See the full report for evidence and other failures.

The historical run recovered from a Windows checkpoint failure: 80 answers and 52 grades survived, and 28 grades without recoverable responses were explicitly requested again. Lost grade token usage is unknown. The recovery record and original answers remain unchanged; the 2026-10-15 work made no generation or judge API calls.

```powershell
# Read-only validation of saved artifacts; no API calls or settings required.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
# Recompute and export from the saved run, without generating new answers.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark summarize --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.render_report --output-dir eval/results/phase5_v2_20261014
```

[benchmark.py](../eval/benchmark.py) now validates the dataset/PDF fingerprints, selection/pilot links, development-only retrieval, answer identity/split, judge inputs/raw grades, and derived metrics/queue. [render_report.py](../eval/render_report.py) uses that validation before writing. Missing answers enter both the review queue and CSV; failed/missing answers stay in score denominators, and a run with no successes displays no mean latency. Export stops before writing if the existing review CSV contains human notes or changed review statuses; keep human work in a separate review file. Checksums detect mismatches, not independent truth or human approval.

On 2026-10-15 the 22-chunk deployment bundle passed validation. `eval.check_trace` stopped before generation because LangSmith is unconfigured. Docker's Linux engine remained unavailable, so Linux/Cloud execution and a public URL were still unverified then. On 2026-10-16 the app ran on Community Cloud, the first Linux execution evidence; startup time, memory, and restart behavior were not measured.

## Results and reproduction

Evidence files: [baseline](../eval/results/phase5_baseline.json), [agent review](../eval/results/phase5_agent_review.json), [metrics](../eval/results/phase5_metrics.json), [blank human review](../eval/results/phase5_human_review.template.json). The run records model `claude-sonnet-5-5`, local E5 embeddings, top three, corpus/index hashes, library versions, source hashes, all generated claims, and original retrieval. Only the current question is passed to RAG; evaluation annotations are added outside generation.

| Measure | Observed result |
| --- | --- |
| Completed requests | 10/10; no errors or missing questions |
| Retrieval Hit@3 | 8/8 |
| Multi-document page coverage | 2/2 |
| All required reference quotes retrieved | 8/8 |
| Unanswerable-question abstention contract | 2/2 |
| Mean RAG latency | 3326.96 ms; min 1071.48, max 7021.95; initialization excluded |
| Agent-reviewed correctness | 9/10; independent human grading pending |
| Agent-reviewed grounding | 10/10 |

**Observed limitation — q08:** CFO and prior legal review are supported by the matching 720만원/12-month example, but the answer omits the general applicable threshold and sufficiently explicit timing required by the broader rubric. Those general legal-review clauses are not in the retrieved top three. It is graded incorrect under the full rubric, even though its emitted claims are grounded. No expected-answer text was inserted into the prompt to conceal this failure.

```powershell
# Ten billable Claude calls. Each new run gets its own timestamped JSON.
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate
# Recompute the saved baseline and apply the identified agent review without API calls.
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate --report eval/results/phase5_baseline.json --review eval/results/phase5_agent_review.json
# After configuring LangSmith: one generation, then verify remote child runs.
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

The runner writes a checkpoint after every question, preserves retrieved chunks when generation fails, never counts API errors as abstentions, and leaves the ten-success mean unset if any request fails/is missing. Recalculation validates dataset/result hashes; reviews are tied to the exact answers/settings and cannot silently grade another run. Human and agent reviews are distinguished; keyword matching never determines correctness.

## Tracing and deployment implementation

Tracing is opt-in. Explicit root, `retrieval`, and `generation` runs contain question/context/output, not settings or credentials. Writes use bounded network settings; the first failure disables that sink until restart, while ordinary answers continue. `check_trace` reads the remote tree back and requires both completed child runs plus matching output; a successful POST alone is not proof of a verified trace. The owner later supplied the local key; the strengthened checker verified real pages/5/6000 execution on 2026-10-16. See [Phase 6 follow-up](Phase6_RetrievalAndAnswerQuality.md#follow-up-results-and-remaining-work) for the parent-ID fix, token checks, and later grading deferral.

The 208,225-byte [index bundle](../deployment/index_bundle.json) stores the 22 original chunks and precomputed 384-dimensional vectors. It imports into an empty Chroma directory, verifies integrity, and reuses the index on restart. Fresh-import retrieval succeeded with the real query model while document embedding was forbidden. PDFs, settings, and the original local index were not rebuilt. The local Docker Linux daemon was unavailable; the first Linux evidence is the 2026-10-16 Community Cloud deployment, where restart and resource behavior have not yet been measured.

Actual local Edge browser automation verified q01/q07 answers, q09 abstention, source expanders, and reload. Screenshots: [home](../docs/evidence/local-home.png), [chat](../docs/evidence/local-chat.png). Full Cloud instructions and remaining operator steps are in [DEPLOYMENT.md](../DEPLOYMENT.md).

## Historical ten-question evaluation contract

- **Retrieval Hit@3**: among eight answerable questions, count a question once if any accepted document/page appears anywhere in the original top three retrieved chunks.
- **Multi-document Coverage**: for each of q07/q08, every required evidence group must have at least one candidate page in the top three. Groups are AND; candidates within `any_of` are OR.
- **Answer Correctness**: manually review all ten answers using `grading_criteria` and the actual retrieved passages. `expected_answer` is a reference; `answer_keywords` do not automatically determine correctness.
- **Abstention**: manually assess whether the two unanswerable questions are declined appropriately. An API error is not a correct abstention.
- **Latency**: report mean response time for the ten-question run. Report failed or missing runs explicitly rather than hiding them in an average or claiming a complete run.
- Page matches are coarse evidence. Review the actual chunk text against candidate quotes. Empty `evidence_groups` never count as retrieval success, and evaluation answers/annotations must stay outside the index and answer context.

## Deployment decisions and completion gate

- Confirm the same Python and working dependency versions locally and on Cloud. Verify the chosen prebuilt-index strategy before considering the startup-build fallback.
- Configure server-side Claude/LangSmith settings and provider usage controls. Real `.env` and `.streamlit/secrets.toml` files must not be published.
- Record actual model names, corpus/chunk settings, and run date with results. Do not invent performance targets or claim that ten synthetic questions establish real enterprise performance.
- This phase remains in progress while trace evidence or formal public acceptance checks are missing. Full human grading is deferred by the user's 2026-10-14 instruction; the review queue remains explicitly unverified until selective review is performed. AI evaluation completion does not mean human validation or deployment completion.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the evaluation contract and portfolio/deployment completion criteria; all execution evidence remains pending. |
| 2026-10-14 | Implemented evaluation, error-isolated tracing, remote trace verifier, portable index, and the missing local UI. Recorded 10 live results, agent review, local browser evidence, and deploy instructions. Human review, LangSmith credentials, and public deployment remain pending. Separate dev-log unavailable. |
| 2026-10-15 | Reconciled the completed 60-question evaluation; added read-only artifact verification, cross-run/grade validation, missing/failed-answer exports, and protection for human CSV notes. 243 tests passed in 20.25 seconds. Preserved original model outputs and application settings; live trace/public deployment pending. Separate dev-log unavailable; changes recorded here. |
| 2026-10-16 | Audited the implementation and planned remaining release tasks; 243 tests passed in 60.40 seconds, with dependency/artifact/bundle checks passing. Added a consolidated roadmap and dated verification record. Preserved runtime code and saved evaluations; human review remains deferred. Separate dev-log unavailable; changes recorded here. |
| 2026-10-16 | Deployed `main` to Streamlit Community Cloud ([public URL](https://enterprise-rag-demo-project.streamlit.app/)) and made the repository public; the owner confirmed it works in a private window. Documented `RAG_TOP_K=3` in example files and recorded the URL. Runtime code and evaluations unchanged; formal acceptance checks and the real trace remain pending. |
| 2026-10-16 | Updated real tracing to verified for local pages/5/6000 execution after the Phase 6 parent-ID/usage fixes. Cloud tracing and formal Cloud checks are separate. Later AI-review credit exhaustion and owner deferral are recorded in Phase 6. Separate dev-log unavailable. |

---

# Phase 5 — 평가·실행 추적·배포 `🚧 진행 중`

> 실제 평가 결과, 실행 Trace, 공개 URL로 애플리케이션을 검증하고 보여준다.

**상태**: 🚧 2026-10-14 기존 10문항·확대 60문항 AI 평가 완료, 2026-10-15 보고서 보강, 2026-10-16 오프라인 재검증 통과. 2026-10-16 Streamlit Community Cloud에 공개 데모 배포. 사람 검토는 후속으로 보류하며 실제 LangSmith Trace·정식 Cloud 인수 검사는 대기.\
**선행 조건**: [Phase 4](Phase4_StreamlitInterface.md) 로컬 동작 검증, API 사용 준비, LangSmith 프로젝트, GitHub·Streamlit 배포 접근 권한.\
**예정 기술**: Python 평가 실행 코드, JSON 결과, 참고 근거 기반 AI 채점과 추후 사람 검토 목록, LangSmith, Streamlit Community Cloud.

## 개요

기존 10문항 결과를 보존하고 아래 기준으로 평가를 확대한 뒤 검색·생성 Trace와 배포 환경을 검증한다. AI 채점과 사람 확인은 구분해 표시한다. 실제 추적 연결과 공개 배포는 이번 평가 실행 범위에 포함하지 않는다.

누락된 Phase 4 화면을 먼저 구현하고 로컬 검증했다. 사용자가 `https://github.com/SoyeonAhn3/enterprise-rag.git`를 지정하고 Streamlit·GitHub 계정 연결을 확인했다. 로컬 Claude 키는 동작하며 LangSmith 키는 미설정이다. 2026-10-16 `main`을 Streamlit Community Cloud에 배포했고([enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/)) 같은 날 저장소를 공개로 전환했다. 사용자가 시크릿 창에서 동작을 확인했고, 로그인 없는 요청으로 앱 접근을 확인했다.

## Task 및 현재 증빙

| 산출물 | 완료 기준 | 검증 방향 |
| --- | --- | --- |
| ✅ 평가 실행 | 10회 결과에 검색·답변·설정·오류·시간 보존 및 지표 재현 | 실제 10문항 완료. 중간 저장·실패·분모·무결성 테스트 통과 |
| 🚧 검토 | 검토자를 정확히 구분하고 전체 답변을 근거·채점 기준에 대조 | 에이전트 검토 정답 9/10·근거 충족 10/10 기록. 해당 결과에 연결된 사람 검토 양식은 미작성 |
| ✅ 확대 AI 평가 | 60문항 고정, 개발용 결과로만 설정 선택, 동일 질문 답변 비교와 근거를 확인한 AI 검토 | 12사례 사전 시험·검색 설정 4개 비교·B(800/120/k=5) 선택. 답변 120개·AI 채점 120개·사람 검토 목록 34건 저장 |
| ✅ 오프라인 재현 | 산출물 연결 검증 및 실패·누락을 내보내기에 표시 | 읽기 전용 `benchmark verify`, 지표·검토 목록 재계산. 실행 혼합·잘못된 채점·답변 누락·사람 CSV 메모 회귀 검사 |
| ✅ LangSmith | 검색·생성 분리, 추적 오류 시 답변 유지, 실제 원격 실행 확인 | ✅ 2026-10-16 로컬 pages/5/6000 실제 원격 대조 완료. Phase 6 후속 참고. Cloud 추적과 구분. |
| 🚧 공개 배포 | 방문자 키 없는 공개 사용 흐름 및 재시작 후 인덱스 로딩 | 실제 로컬 브라우저·번들 가져오기 및 재로딩 통과. 2026-10-16 Community Cloud 배포, 사용자 시크릿 창 확인 통과. q01·q07·q09 정식 검사·재시작·자원 확인은 대기 |
| 🚧 포트폴리오 | 실측·실패 분석·스크린샷·실제 추적 및 공개 링크 | 영문·국문 문서·로컬 스크린샷·JSON 준비. 2026-10-16 공개 URL 기록. 공개 화면 스크린샷·Trace 증빙은 아직 없음 |

구현 파일: [eval/evaluate.py](../eval/evaluate.py), [tracing.py](../tracing.py), [eval/check_trace.py](../eval/check_trace.py), [deployment.py](../deployment.py), 사전 계산 인덱스 번들, Streamlit 설정·화면, 테스트, [배포 안내](../DEPLOYMENT.md). 기존 패키지를 교체하지 않고 Streamlit을 설치했고 `pip check`에서 충돌이 없었다. `.env`에는 누락된 선택적 추적·세션 설정만 추가해 Claude 키를 보존했다.

최초 Phase 5 점검의 전체 로컬 테스트는 2026-10-16 **243개, 60.40초**로 통과했다. 이후 [Phase 6 후속](Phase6_RetrievalAndAnswerQuality.md#후속-결과와-남은-작업)에서 테스트 305개가 통과했다. 의존성, 저장 평가 산출물, 청크 22개 배포 번들 검사도 통과했다. 해당 Phase 5 점검에서는 새 모델 답변·AI 채점을 생성하지 않았다. [2026-10-16 검증 기록](../eval/results/phase5_v2_20261014/verification_20261016.json)에 근거를 남겼다. 이전 20.25초 실행과 보고서 회귀 검사 20개 추가 내역은 [2026-10-15 기록](../eval/results/phase5_v2_20261014/verification_20261015.json)에 보존한다. 자동 테스트는 실제 모델 평가·브라우저 검사와 구분한다.

## 2026-10-16 점검 이후 남은 작업

[개발 현황 및 로드맵](DevelopmentStatusAndRoadmap.md)에 구현 근거와 이후 단계 제안을 모았다. 기존 공개 MVP를 먼저 완료한다. 아래는 현재 단계만 상세화한 작업이며 CI·설정 문서 정리는 새 배포 준비 제안이다. Phase 1~4의 구현 누락으로 간주하지 않는다.

| Task·우선순위 | 작업 내용·대상 파일 | 완료 기준 | 검증 방법 | 상태 |
| --- | --- | --- | --- | --- |
| 5.R1 / P0 | 소스·문서·실제 설정·저장 평가·의존성·테스트 점검 | 새 답변 생성 없이 현재 상태를 날짜와 재현 근거로 확인 | 기존 전체 테스트, `pip check`, `benchmark verify`, `deployment.py check`. 위 검증 기록 참조 | ✅ 완료 |
| 5.R2 / P0 | 분리된 프로젝트 체크아웃에서 배포본 식별. `.env.example`, `.streamlit/secrets.toml.example`, README, 기존 기획서를 실제 Claude·로컬 E5·벡터 번들에 맞춤. `RAG_TOP_K=3` 명시 | 배포 설정이 일관됨. 오래된 OpenAI·네이티브 인덱스 예시를 현재 절차로 오인하지 않음. 품질 변경은 별도로 식별 | 배포 파일과 점검 작업 폴더 비교, 비밀값을 제외한 설정 로딩과 번들 호환성 확인 | 🟡 일부 완료(2026-10-16): 분리 체크아웃에서 배포본 게시, 예시 파일에 `RAG_TOP_K=3` 명시·로딩 확인. 기존 기획서에는 OpenAI 시기 문구가 남아 있음 |
| 5.R3 / 시작 P0, CI P1 | 새로운 Linux·Python 3.12 환경과 시작 동작 검증. `.github/workflows/ci.yml`에 작은 오프라인 CI 추가(예정 파일) | Linux 의존성·기존 검사 통과. 문서 임베딩 없이 첫 가져오기·재시작 성공. 실제 질문 모델 시작은 별도 증빙 | 새 설치, 로드맵의 오프라인 명령 4개, 캐시 다운로드·재시작 확인. 시작 시간·메모리 실측 | 🔲 예정 |
| 5.R4 / P0 | 운영자 LangSmith 설정 후 기존 `eval.check_trace` 실행 | 원격 루트·완료된 검색 및 생성 하위 실행이 실제 답변과 일치. 실패 격리 유지 | 실제 생성 1회와 원격 재조회, 로컬 `data/trace_check.json`, 기존 실패 격리 테스트 | ✅ 2026-10-16 로컬 pages/5/6000 실제 원격 대조 완료. Phase 6 후속 참고. Cloud 추적과 구분. |
| 5.R5 / P0 | 식별한 배포본의 `app.py`를 Community Cloud에 배포. 서버 시크릿·제공업체 사용량 제어 설정 | 새 방문자가 키 없이 q01·q07 근거 답변과 q09 보류 확인. 새로고침·재시작 정상. 사용량 제어 설정 기록 | 시크릿 브라우저, 공개 URL, 시작·재시작 로그, 스크린샷. 공유 리소스의 순차 처리 때문에 세션 2개의 대기 동작도 확인 | 🟡 2026-10-16 배포([공개 URL](https://enterprise-rag-demo-project.streamlit.app/)), 사용자 시크릿 창 확인만 완료. q01·q07·q09 정식 검사·재시작·사용량 제어·세션 2개 확인은 미기록 |
| 5.R6 / P0 | `README.md`, `README_ko.md`, `DEPLOYMENT.md`, 본 문서를 실제 배포본과 맞춤 | 실제 URL·배포 설정·Trace·구간별 AI 점수·남은 한계가 일치. 사람 검증 완료로 표시하지 않음 | 새 세션에서 공개 링크·증빙 확인, 배포 설정·결과와 대상 코드 비교 | 🟡 양쪽 README·DEPLOYMENT.md·본 문서에 URL 기록. Trace 증빙은 5.R4 선행 |

권장 순서는 **5.R2 → 5.R3 시작 검증 → 5.R5 → 5.R6**이다. 5.R4는 키가 준비되면 진행하여 Phase 완료 전에 끝낸다. CI는 시작 검증과 함께 준비할 수 있다. 남은 작업량은 **개발자 1명 기준 2~3작업일**로 추정하며 접근 권한·계정 준비·플랫폼 장애 대기는 제외한다. 납기 약속이 아니다. 운영자는 계정·서버 설정을 제공하고 개발자는 구현·검증·증빙 갱신을 수행한다.

별도 품질 변경 결정을 기록하기 전에는 기존 MVP의 k=3을 유지한다. k=5는 이미 지원·평가했고 제안한 Phase 6에서 우선 적용을 검토한다. 현재 상태를 문서화하려고 답변 120개 전체 평가를 다시 실행하지 않는다.

기존에 기록된 사용자 결정에 따라 사람 검토는 계속 뒤로 미룬다. 검토 목록 34건과 AI·사람 판정 구분을 유지하고 선택 검토는 추후 재개한다. 이를 추가 배포 선행 조건으로 바꾸지 않는다. 실제 공개 동작과 Trace 검증이 없으면 Phase 완료로 표시할 수 없다. 2026-10-16 점검 자체에서는 원격 저장소 조회·배포·실제 모델 및 브라우저 검사를 수행하지 않았으며, 배포는 같은 날 이후에 진행했다.

## 확대 평가 기준 — 실행 전에 확정 (2026-10-14)

사용자 요청에 따라 AI 평가를 먼저 수행하고 전체 사람 채점은 뒤로 미룬다. 확인이 필요한 답변·문장·누락 항목·관련 원문·이유를 검토 목록에 남긴다. AI 통과 결과를 사람 검증 결과로 표시하지 않으며 실험으로 운영 설정을 자동 변경하지 않는다.

1. 문서 기반 질문 60개를 확정한다. 개발용 40개는 단일 문서 20·다중 문서 12·답변 불가 8개, 최종 확인용 20개는 10·6·4개다. 기존 10개는 개발용에 포함하고 유사 표현 질문은 같은 묶음에 둔다. 작은 가상 문서의 규칙을 공유하므로 최종 확인용도 외부 독립 벤치마크는 아니다.
2. 모델 호출 전에 참고 원문을 실제 PDF 페이지와 대조한다. 필수 근거 그룹이 채점에 필요한 사실을 포함하도록 하며 q08은 일반 법무 검토 조건도 포함한다. 기존 10문항 파일과 결과는 보존하고 별도 버전의 데이터셋을 만든다. 참고 정답·채점 기준·최종 확인용 정답은 RAG 생성 프롬프트나 인덱스에 넣지 않는다.
3. 저장된 기존 10개 답변과 의도적으로 틀리거나 근거가 없는 사례로 AI 채점기를 먼저 시험한다. q08 누락을 탐지하는지 확인하고 확대 실행 전에 채점 프롬프트를 고정한다. AI 채점에는 질문·기준·참고 원문·검색 청크·생성 답변을 별도 호출로 전달한다. 동일한 Claude 모델을 사용할 수 있으며 독립된 사람 또는 다른 모델의 평가가 아님을 표시한다.
4. 개발용 질문으로 검색만 비교한다. A=800자/중복120자/k=3, B=800/120/5, C=500/120/3, D=800/0/3이다. 별도 인덱스 폴더에 같은 PDF와 E5를 사용한다. 필수 원문 그룹 전체 포함률 → 개별 그룹 포함률 → 페이지 적중률 → 작은 k → 설정 ID 순서로 대안 하나를 선택하고, 답변 생성과 최종 확인용 결과 확인 전에 선택을 고정한다.
5. A와 선택한 대안을 같은 개발용 40개와 최종 확인용 20개에 실행한다. 질문별로 설정 실행 순서를 번갈아 적용한다. 모델·답변 프롬프트·채점 기준·문서는 고정한다. 답변과 채점의 모든 시도, 오류, 토큰 사용량을 남기고 자동 재시도나 실패 제외를 하지 않는다. 질문·설정별 1회 실행이므로 통계적 유의성을 주장하지 않는다.
6. 개발용/최종 확인용 지표, 같은 질문의 전후 결과, 사람 검토 목록을 공개한다. 사람 검토는 추후 의심 답변과 재현 가능한 AI 통과 표본을 확인하는 작업으로 남긴다. 실제 LangSmith 및 공개 배포 검증은 별도 미완료 항목이다.

| 평가 항목 | 판정 및 분모 |
| --- | --- |
| Retrieval Hit@k | 답변 가능한 질문 중 허용된 근거 페이지가 하나 이상 검색된 비율. k를 함께 표시한다. |
| 필수 근거 전체 포함 / 그룹 포함률 | 필요한 원문 그룹을 모두 찾은 질문 비율과 개별 그룹을 찾은 비율을 구분한다. 공백만 무시해 대조하며 빈 근거는 검색 성공으로 세지 않는다. |
| AI 정확성·완전성 | 필수 사실이 맞고 조건이 모순되지 않아야 한다. 문서에 답이 없으면 보류해야 한다. 전체 및 답변 가능한 질문 성적을 따로 표시하고 오류·누락도 분모에 남긴다. |
| AI 근거 충족 | 생성한 사실 주장이 검색 원문으로 뒷받침되는지 확인한다. 근거가 있어도 필요한 설명이 빠지면 정답이 아닐 수 있다. 실제 답변과 보류를 구분해 표시한다. |
| 확인 필요 판정 | 조건 누락, 근거 없는 주장, 경계값·AND/OR·시점 오류, 불필요한 보류, 근거 충돌, 모호한 채점 기준을 표시한다. 실제 문제 문장·기준 ID·관련 원문·이유를 남긴다. 누락은 빈 문장과 빠진 사실을 명시한다. |
| 오류·시간 | RAG 오류, AI 채점 오류, 정상 보류를 구분한다. 성공 응답 평균·중앙값·p95와 전체 시도 수를 기록하며 초기화·AI 채점 시간은 RAG 응답시간에서 제외한다. API 토큰은 기록하되 금액을 추정해 만들지 않는다. |

**구현·실행 상태:** 2026-10-14 실행 완료, 2026-10-15 오프라인 검증 완료. 아래 기존 10문항 성적은 당시 기준의 과거 증빙으로 보존한다.

## 확대 결과 및 오프라인 검증

[확대 보고서](../eval/results/phase5_v2_20261014/report.md)와 [지표](../eval/results/phase5_v2_20261014/metrics.json)에 질문 60개·답변 120개·AI 채점 120개를 기록했다. A는 800/120/k=3, B는 800/120/k=5다. 개발용 검색 결과만으로 B를 선택한 뒤 최종 확인을 실행했으며 앱 기본값은 k=3을 유지한다.

| 구분 | A AI 정답 | B AI 정답 | A / B 성공 응답 평균 |
| --- | --- | --- | --- |
| 개발용 40문항 | 35/40 (87.5%) | 39/40 (97.5%) | 3.00 / 3.44초 |
| 최종 확인용 20문항 | 13/20 (65.0%) | 15/20 (75.0%) | 3.05 / 2.88초 |

생성과 채점은 같은 Claude 모델의 별도 호출이다. 사람의 독립 검증이 아닌 AI 점수다. [검토 목록](../eval/results/phase5_v2_20261014/review_queue.csv)은 질문 23개에 대한 의심 답변 26건과 AI 통과 표본 8건이다. q08/A는 일반 조건 누락에 대한 채점 해석 차이를, q31/B는 필요한 기한 근거를 검색하지 못해 보류한 한계를 보여 준다. 원문과 다른 실패 사례는 전체 보고서에 있다.

기존 실행에서는 Windows 중간 저장 오류 뒤 답변 80개·채점 52개를 복구하고, 응답을 복구할 수 없는 채점 28개만 명시적으로 다시 요청했다. 유실된 채점 토큰 사용량은 알 수 없다. 복구 기록과 답변 원본은 보존했으며 2026-10-15 작업에서는 생성·채점 API를 호출하지 않았다.

```powershell
# 저장 산출물을 읽기 전용으로 검증. API 호출·설정 불필요.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
# 저장 실행에서 지표와 보고서를 재생성. 새 답변 생성 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark summarize --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.render_report --output-dir eval/results/phase5_v2_20261014
```

[benchmark.py](../eval/benchmark.py)는 데이터셋·PDF 해시, 설정 선택·사전 시험 연결, 개발용 검색, 답변 ID·묶음, 채점 입력·원본 판정, 재계산 지표·목록을 검증한다. [render_report.py](../eval/render_report.py)는 쓰기 전에 같은 검증을 수행한다. 누락 답변도 검토 목록·CSV에 포함하고 실패·누락은 정답률 분모에 남긴다. 성공 응답이 없으면 평균 시간을 표시하지 않는다. 기존 검토 CSV에 사람 메모나 변경된 검토 상태가 있으면 쓰기 전에 중단하므로 사람 작업은 별도 검토 파일에 보존한다. 해시는 불일치를 탐지하며 내용의 독립 검증이나 사람 승인을 의미하지 않는다.

2026-10-15 청크 22개 배포 번들 검증에 통과했다. `eval.check_trace`는 LangSmith 미설정으로 생성 전에 중단했다. Docker Linux 엔진도 실행되지 않아 당시 Linux·Cloud 실행과 공개 URL은 미검증이었다. 2026-10-16 Community Cloud에서 앱이 실행되어 첫 Linux 실행 근거를 얻었으며, 시작 시간·메모리·재시작 동작은 측정하지 않았다.

## 실측 결과 및 재현

증빙: [실행 원본](../eval/results/phase5_baseline.json), [에이전트 검토](../eval/results/phase5_agent_review.json), [지표](../eval/results/phase5_metrics.json), [사람 검토 양식](../eval/results/phase5_human_review.template.json). 결과에 `claude-sonnet-5-5`, 로컬 E5, 상위 3개, 문서·인덱스 해시, 라이브러리 버전, 소스 해시, 전체 주장과 원래 검색을 기록했다. RAG에는 현재 질문만 전달하고 평가 주석은 생성 밖에서 붙인다.

| 지표 | 실제 결과 |
| --- | --- |
| 요청 완료 | 10/10, 오류·누락 없음 |
| Retrieval Hit@3 | 8/8 |
| 다중 문서 페이지 Coverage | 2/2 |
| 필수 원문 발췌 전체 검색 | 8/8 |
| 답변 불가 질문 보류 계약 | 2/2 |
| 평균 RAG 처리 시간 | 3326.96 ms, 최소 1071.48·최대 7021.95, 초기화 제외 |
| 에이전트 검토 정답 | 9/10, 독립적인 사람 채점 대기 |
| 에이전트 검토 근거 충족 | 10/10 |

**관찰한 한계 — q08:** CFO와 법무 사전검토는 720만원·12개월 계약 사례로 뒷받침된다. 그러나 일반적인 적용 기준과 명확한 검토 시점 설명이 전체 채점 기준에 부족하다. 해당 일반 조항은 상위 3개 문맥에 없다. 생성한 주장에는 근거가 있지만 전체 기준에서는 오답으로 기록했다. 이 실패를 감추기 위해 참고 정답을 프롬프트에 넣지 않았다.

```powershell
# 과금되는 Claude 10회 호출. 실행마다 새 시간명 JSON 생성
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate
# API 호출 없이 저장 결과와 검토자가 명시된 에이전트 검토로 지표 재계산
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate --report eval/results/phase5_baseline.json --review eval/results/phase5_agent_review.json
# LangSmith 설정 후 생성 1회, 원격 하위 실행 재조회 검증
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

질문마다 중간 결과를 저장하며 생성 실패 시에도 검색 청크를 보존한다. API 오류를 보류로 계산하지 않고 실패·누락이 있으면 전체 10회 성공 평균을 비워 둔다. 재계산 시 데이터·결과 해시를 확인하고, 검토를 정확한 답변·설정에 연결해 다른 실행을 잘못 채점하지 않게 한다. 사람·에이전트 검토를 구분하며 키워드 일치로 정답을 판정하지 않는다.

## 실행 추적 및 배포 구현

추적은 선택적으로 켠다. 루트·`retrieval`·`generation`에 질문·문맥·출력을 기록하며 키·설정 객체는 넣지 않는다. 네트워크 요청을 제한하고 첫 전송 실패부터 재시작 전까지 해당 추적기를 중단해도 답변은 유지한다. `check_trace`는 실제 원격 실행을 재조회하여 두 하위 실행 완료와 답변 일치를 확인한다. POST 성공만을 Trace 검증으로 간주하지 않는다. 이후 사용자가 로컬 키를 입력했고 강화한 검증기로 2026-10-16 pages/5/6000 실제 원격 대조를 완료했다. 상위 ID 수정·토큰 검증·후속 채점 보류는 [Phase 6 후속](Phase6_RetrievalAndAnswerQuality.md#후속-결과와-남은-작업)을 참고한다.

208,225바이트 [인덱스 번들](../deployment/index_bundle.json)은 원래 청크 22개와 384차원 사전 계산 벡터를 담는다. 빈 Chroma 폴더에 가져와 무결성을 검증하고 이후 재사용한다. 문서 임베딩을 금지한 채 신규 가져오기와 실제 질문 모델 검색에 성공했다. PDF·설정·기존 로컬 인덱스를 재생성하지 않았다. 로컬 Docker Linux 데몬은 실행되지 않았다. 첫 Linux 실행 근거는 2026-10-16 Community Cloud 배포이며, 재시작·자원 동작은 아직 측정하지 않았다.

실제 로컬 Edge 브라우저 자동화로 q01·q07 답변, q09 보류, 출처 펼치기, 새로고침을 확인했다. 스크린샷: [초기 화면](../docs/evidence/local-home.png), [대화](../docs/evidence/local-chat.png). Cloud 설정과 남은 운영자 절차는 [DEPLOYMENT.md](../DEPLOYMENT.md)에 있다.

## 기존 10문항 평가 기준

- **Retrieval Hit@3**: 답변 가능한 8문항에서 허용된 문서·페이지가 원래 검색된 상위 3개 청크 중 하나 이상에 있으면 질문당 한 번 적중으로 계산한다.
- **Multi-document Coverage**: q07·q08 각각에서 모든 필수 근거 그룹의 후보 페이지가 하나 이상 상위 3개에 있어야 한다. 그룹 사이는 AND, `any_of` 후보 사이는 OR다.
- **Answer Correctness**: `grading_criteria`와 실제 검색 발췌로 답변 10개를 수동 검토한다. `expected_answer`는 참고 설명이며 `answer_keywords`로 자동 정답 판정하지 않는다.
- **Abstention**: 답이 없는 2문항을 적절히 보류했는지 수동 검토한다. API 오류를 올바른 보류로 계산하지 않는다.
- **Latency**: 질문 10개 실행의 평균 응답시간을 기록한다. 실패·누락을 평균 안에 숨기거나 전체 실행 완료로 표시하지 않고 별도로 알린다.
- 페이지 적중은 거친 근거 확인이다. 후보 발췌와 실제 청크 본문을 대조한다. 빈 `evidence_groups`는 검색 성공으로 처리하지 않으며, 평가 정답·주석은 인덱스와 답변 문맥에서 제외한다.

## 배포 결정 사항 및 완료 조건

- 로컬과 Cloud의 Python 및 작동하는 의존성 버전을 맞춘다. 시작 시 인덱스 생성 예비안을 검토하기 전에 사전 생성 인덱스 로딩을 검증한다.
- 서버 Claude·LangSmith 설정과 제공업체 사용량 제어를 준비한다. 실제 `.env`와 `.streamlit/secrets.toml`은 공개하지 않는다.
- 실제 모델명, 문서·청크 설정, 실행 날짜를 결과에 기록한다. 성능 목표를 임의로 만들거나 합성 질문 10개로 실제 기업 문서 성능을 입증했다고 주장하지 않는다.
- 실제 Trace 증빙 또는 정식 공개 인수 검사가 남아 있으면 진행 중 상태를 유지한다. 2026-10-14 사용자 요청에 따라 전체 사람 채점은 뒤로 미루며 선택 검토 전까지 검토 목록은 미확인으로 표시한다. AI 평가 완료를 사람 검증이나 배포 완료로 표시하지 않는다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 평가 기준과 포트폴리오·배포 완료 조건 신규 작성. 실행 증빙은 모두 후속 검증 대상으로 기록함. |
| 2026-10-14 | 평가 실행·오류를 분리한 추적·원격 검증기·인덱스 번들·누락된 로컬 화면 구현. 실제 10문항·에이전트 검토·브라우저 증빙·배포 안내 기록. 사람 검토·LangSmith 키·공개 배포는 대기. 별도 dev-log 미설치. |
| 2026-10-15 | 완료된 60문항 평가 반영. 읽기 전용 산출물 검증, 실행 간 연결·채점 검증, 누락·실패 답변 내보내기, 사람 CSV 메모 보호 추가. 테스트 243개·20.25초 통과. 기존 모델 출력·앱 설정 보존. 실제 Trace·공개 배포 대기. 별도 dev-log 미설치로 여기에 변경 이력 기록. |
| 2026-10-16 | 구현 상태 점검 및 잔여 배포 Task 계획. 테스트 243개·60.40초와 의존성·산출물·번들 검사 통과. 통합 로드맵·당일 검증 기록 추가. 실행 코드와 기존 평가 보존, 사람 검토 보류 유지. 별도 dev-log 미설치로 여기에 이력 기록. |
| 2026-10-16 | `main`을 Streamlit Community Cloud에 배포([공개 URL](https://enterprise-rag-demo-project.streamlit.app/))하고 저장소를 공개로 전환. 사용자가 시크릿 창에서 동작 확인. 예시 파일에 `RAG_TOP_K=3` 명시, URL 기록. 실행 코드·평가는 변경하지 않음. 정식 인수 검사와 실제 Trace는 대기. |
| 2026-10-16 | Phase 6의 상위 ID·토큰 기록 수정 후 로컬 pages/5/6000 실제 추적 검증 완료를 반영했다. Cloud 추적·정식 Cloud 검사는 별개다. 이후 AI 채점의 잔액 부족·사용자 보류는 Phase 6에 기록했다. 별도 dev-log 미설치. |
