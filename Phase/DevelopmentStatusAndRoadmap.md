# Development Status and Roadmap

**Reviewed**: 2026-10-19 (Asia/Seoul)\
**Current milestone**: ✅ Agreed portfolio scope complete. Required-item, all-quotation display, and focused citation improvements were published as [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4); 488 software tests passed. The owner reports completing the Cloud 4096-token setting. No required development remains; independent human grading and broader Cloud operations checks stay deferred.\
**Planning assumption**: The user clarified that this project demonstrates RAG understanding, implementation, precision, and measured accuracy. Concurrency testing is excluded from the current scope and Phase 7 usability remains deferred.

**Latest improvements — 2026-10-19:** [Phase 6 closure](Phase6_RetrievalAndAnswerQuality.md#final-portfolio-improvements--2026-10-19), [required-item review](../eval/results/completeness_display_20261019/review.json), [citation review](../eval/results/citation_completeness_20261019/review.json), and [software tests](../eval/results/citation_completeness_20261019/software_tests.json). The first two improvements used seven live answers; the citation follow-up used ten calls, retaining an output-limit failure and intermediate citation issues before four final cases passed Codex review. No judge calls or automatic retries. These known cases do not yield a new overall accuracy score.

**Earlier split-grading checkpoint — 2026-10-19:** [Split grading and rule selection](Phase6_RetrievalAndAnswerQuality.md#separate-grading-and-complete-rule-selection--2026-10-19) separate reference-based correctness from retrieved-only support. Every item is required in the response schema; citations are constrained to existing claim evidence. Dev coverage improves **14/16→16/16** with known-v2 **48/48** retained. **483 tests** passed. Ten live review requests yielded six accepted stages, three validation rejections and one provider error; the comparison is incomplete and semantic judgment inconsistencies remain. No new answers or final questions were evaluated. All 522 protected files, including 515 historical evaluation files, remain unchanged. See [verification](../eval/results/v3_split_checks_20261019/verification.json).

**Earlier refinement — 2026-10-19:** Implemented section-aware context selection, clearer quote/inference instructions, revised grading instructions and saved-answer comparison. **439 software tests passed**. The live dev comparison reused 20 page answers and made **20 new answer + 39 review calls = 59 calls**. Required evidence improved **12/16 → 14/16** and validated outputs **19/20 → 20/20**, but AI passes under the same revised judge remained **17/20 → 17/20**. The original baseline's 15/20 becoming 17/20 on regrade is not an implementation gain. All 434 protected files, including 427 historical evaluation files, were preserved. See [implementation and limits](Phase6_RetrievalAndAnswerQuality.md#v3-development-refinement--2026-10-19), [report](../eval/results/v3_refinement_dev_20261019/report.md) and [verification](../eval/results/v3_refinement_dev_20261019/verification.json). Next: isolate evidence-support grading from reference answers, independently adjudicate disputed cases, and improve remaining approval-table retrieval and claim citations before another dev comparison. Final 20 questions remain unexecuted; no publication or Cloud changes were made.

**Initial v3 dev evaluation — 2026-10-19:** Dataset tooling and v3 preparation passed **409 software tests**, then the unchanged implementation completed a live comparison on the **20 dev questions**. Original AI passes were **14/20 chunks versus 15/20 pages**; complete required-quote coverage was **10/16 versus 12/16**. Actual use was **40 answers + 39 reviews = 79 model calls**, with one page quote-validation failure and no provider/judge errors. Offline artifact verification and report reproduction passed; all 376 baseline files were preserved. Software tests were not rerun in that evaluation turn. See [results and analysis](Phase6_RetrievalAndAnswerQuality.md#v3-development-evaluation--2026-10-19), [report](../eval/results/v3_dev_20261019_1003/report.md) and [verification](../eval/results/v3_dev_20261019_1003/verification.json). Those baseline results remain intact. Historical review recovery was not run; future recovery requires both a new plan and compatibility with the original judge/version.

The initial implementation in the [Phase 6 report](Phase6_RetrievalAndAnswerQuality.md) records 267 passing tests, development complete-evidence retrieval of 32/32 with optional pages/k=5, and six known live cases passing same-model AI review. Code was pushed as [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa). The owner reported setting pages/5/6000 and rebooting Cloud; effective runtime behavior has not been independently checked. The original Phase 5 audit below is preserved as historical evidence.

**Preserved final evaluation:** The earlier [frozen 20-question run](../eval/results/v3_closeout_20261019/report.md) remains complete evidence 12/16, content 15/20, content/citations 13/20, unanswerable abstention 4/4, mean 5.193 seconds. It used six dev plus twenty final answers and zero AI judges. Later focused fixes do not overwrite these scores. The dated checkpoints below and above describe historical states; their pending publication/evaluation tasks are superseded by the current completion record.

## Project objective and evidence priorities

Demonstrate that the developer can explain and implement PDF extraction, chunking, embeddings, retrieval, context construction, grounded generation, and source validation; measure how often the complete required evidence and correct answer are obtained; and explain improvements and remaining failures. Streamlit is the demonstration interface. Production adoption, concurrent-user capacity, UI expansion, and enterprise operations are not current completion requirements.

The earlier follow-up implemented stronger tracing, a frozen paired evaluator, offline auditing, and review-only recovery, with 347 tests at that checkpoint. Historical coverage improved from chunks 37/48 to pages 47/48, then to 48/48 with final-page selection; that old answer run remains incompletely graded. The new v3 dev measurement is separate and does not repair those missing grades. Traces explain how an answer happened; reference questions, scoring rules, and review assess answer quality. Report retrieval coverage, answer correctness, evidence support/condition completeness, and abstention separately. Keep software tests, same-model grades, human review, and final evaluation distinct. API use resumed for v3 on 2026-10-19; the 87 old reviews were outside this execution.

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

## Completion and optional follow-up

The owner approved bounded completion and the later improvements 1, 2, and 4. No mandatory development or new evaluation remains for this portfolio. The original failures and uncompleted reviews are retained.

| State | Work | Result / boundary |
| --- | --- | --- |
| Complete | RAG implementation, tracing, evaluation and demo | Phases 1–6, public URL, local-to-remote trace, frozen final report and owner observations recorded |
| Complete | 1. Required answer items | Seven live answers checked; account-verification documents explicit in all three targeted bank cases |
| Complete | 2. All supporting quotations | All distinct claim quotations displayed; compatibility retained; saved-answer UI checks passed |
| Complete | 4. Observed citation gaps | Four final cases passed Codex source review; earlier failed attempts retained; latest software suite 488 passed |
| Published / owner-reported | Release and Cloud setting | [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4) pushed; owner reports 4096-token setting complete. Fresh latest-release Cloud answers/restart were not independently observed |
| Optional | 3. Complex retrieval and independent validation | Known retrieval gaps remain. Independent human grading is needed only to claim independently graded results; neither is a portfolio completion gate |
| Deferred / separate | Evaluator expansion, 87 old reviews, 34-item human queue, Phase 7, CI and service operations | No new paid run planned. Concurrency remains outside scope |

## Earlier work sequence and decisions — 2026-10-16

**Completed locally:** trace hierarchy and token metadata fixes, real pages/5/6000 remote readback, paired 120-answer attempt records, offline artifact verification, review recovery preparation, validation diagnostics, final-page selection, and 347 passing tests. The earlier answer comparison obtained complete required context in 37/48 chunk cases and 47/48 page cases; the latest retrieval-only selection check reaches 48/48. In the earlier answer run, validated response counts were 59/60 and 57/60. Grading completed only 15/59 and 14/57 eligible responses. Do not turn the raw 14/60 confirmed-pass counts into an accuracy estimate.

**Decision at the 2026-10-16 checkpoint:** defer recharging and the remaining 87 AI reviews. The owner subsequently funded credits on 2026-10-19 for the next evaluation step. Recovery preparation made no API calls; the [historical plan](../eval/results/phase6_review_recovery_selection_20261016/plan.json) targets failed reviews of saved successful answers. Later code and grading-prompt changes mean recovery needs a new plan and compatibility with the original judge/version. Those grades will assess old answers, not the new selector. Recovery stops at the first provider error and preserves earlier results.

At that checkpoint, the follow-up was prepared through the separate enterprise-rag checkout and the answer prompt was unchanged. Later 2026-10-19 work changed context selection, generation/grading instructions and evaluation tooling; the final agreed implementation is now published as [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4). Keep owner-reported Cloud settings separate from verified local execution, and retain the original final-evaluation and human-review limitations.

## Reproducible local checks

Run from the project root using the existing environment:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement verify --output-dir eval/results/v3_refinement_dev_20261019
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/v3_dev_20261019_1003
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
| 2026-10-19 | Implemented and tested dataset tooling and v3 preparation (409 tests). Preserved original data, reports and runtime RAG behavior. Next: explicitly resumed live dev/final evaluation; no API calls or publication. History recorded here because dev-log is unavailable. |
| 2026-10-19 | Recorded resumed API use and completed v3 dev evaluation: 79 model calls, original passes 14/20 versus 15/20, coverage 10/16 versus 12/16. Verified artifacts and preserved baseline files; prioritized grading clarity, context selection, quote generation and fixed-code final evaluation. No runtime edits or publication; dev-log unavailable. |
| 2026-10-19 | Completed dev refinement and saved-answer comparison: 439 tests, 59 new model calls, evidence 12/16→14/16 and validated outputs 19/20→20/20; same-judge passes unchanged at 17/20. Preserved 434 files. Prioritized grading isolation, disputed-case review, approval-table retrieval and claim citations; final evaluation/publication pending. Dev-log unavailable; history recorded here. |
| 2026-10-19 | Published 192 reviewed files as 8686fff, then implemented separate grading and rule-topic selection locally. 483 tests; dev evidence 14/16→16/16, known-v2 48/48 retained. Live review partial: 10 requests, 6 accepted stages, 3 validation rejections, 1 provider error. Preserved 522 files; new answers/final evaluation and independent adjudication pending. Dev-log unavailable; recorded here. |
| 2026-10-19 | Bounded closeout: 484 tests, 26 answers/no judges; final content 15/20 and strict 13/20 by Codex. Demo replay/restart passed, 554 old files retained; human review/publication separate. Further evaluator work deferred; dev-log unavailable. |
| 2026-10-19 | Reconciled all completed improvements, release 175bda7, 488-test evidence, and the owner’s Cloud setting report. Closed required portfolio work; kept optional retrieval/independent review and historical results explicit. Documentation only; dev-log unavailable. |

---

# 개발 현황 및 향후 개발 계획

**점검일**: 2026-10-19 (한국 시간)\
**현재 단계**: ✅ 합의한 포트폴리오 범위 완료. 필수 항목·모든 인용 표시·관측한 인용 보완을 [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4)으로 게시했고 소프트웨어 테스트 488개가 통과했다. 사용자가 Cloud 4096토큰 설정 완료를 보고했다. 남은 필수 개발은 없으며 독립 사람 채점·폭넓은 Cloud 운영 검사는 보류한다.\
**계획 전제**: 사용자가 목표를 RAG 이해·구현·정교함·측정한 정확도를 보여주는 것으로 명확히 했다. 동시 접속 검사는 현재 범위에서 제외하며 Phase 7 사용성은 계속 보류한다.

**최신 개선 — 2026-10-19:** [Phase 6 완료 기록](Phase6_RetrievalAndAnswerQuality.md#최종-포트폴리오-개선--2026-10-19), [필수 항목 검토](../eval/results/completeness_display_20261019/review.json), [인용 검토](../eval/results/citation_completeness_20261019/review.json), [소프트웨어 테스트](../eval/results/citation_completeness_20261019/software_tests.json). 앞의 두 개선은 실제 답변 7개, 인용 후속은 전체 10회 호출이다. 출력 한도 실패·중간 인용 문제를 보존하고 최종 4사례가 Codex 검토를 통과했다. 별도 채점·자동 재시도는 없다. 알려진 사례이므로 새 전체 정확도를 산출하지 않는다.

**이전 채점 분리 점검 — 2026-10-19:** [채점 분리·규정 선택](Phase6_RetrievalAndAnswerQuality.md#채점-분리와-규정-선택-보완--2026-10-19)으로 참고 정답 기반 정확성과 검색 근거만의 근거성을 분리했다. 응답의 모든 항목을 필수화하고 인용은 기존 주장 근거에 한정한다. 개발용 근거 **14/16→16/16**, 알려진 v2 **48/48** 유지, **테스트 483개** 통과다. 실제 채점 10회 중 6개 단계를 채택하고 3개는 검증에서 거부했으며 1개는 제공업체 오류다. 비교는 미완료이고 의미 판정 불일치도 남았다. 새 답변·최종 문항은 평가하지 않았다. 과거 평가 515개를 포함한 보호 파일 522개를 보존했다. [검증](../eval/results/v3_split_checks_20261019/verification.json)을 참고한다.

**이전 후속 개선 — 2026-10-19:** 절 제목을 활용한 문맥 선택, 인용·추론 지시, 채점 지시와 저장 답변 비교 도구를 구현했다. **소프트웨어 테스트 439개를 통과**했다. 실제 개발용 비교는 이전 페이지 답변 20개를 재사용하고 **새 답변 20회 + 채점 39회 = 모델 59회**를 호출했다. 필수 근거는 **12/16 → 14/16**, 출력 검증은 **19/20 → 20/20**으로 개선했지만 같은 새 채점 기준의 AI 통과는 **17/20 → 17/20**이다. 이전 답변의 원래 15/20이 재채점에서 17/20이 된 것은 구현 개선이 아니다. 보호 대상 434개, 그중 과거 평가 파일 427개를 보존했다. [구현과 한계](Phase6_RetrievalAndAnswerQuality.md#v3-개발-후속-개선--2026-10-19), [보고서](../eval/results/v3_refinement_dev_20261019/report.md), [검증](../eval/results/v3_refinement_dev_20261019/verification.json)을 참고한다. 다음은 참고 정답과 근거성 채점 분리, 논쟁 사례의 독립 판정, 남은 결재 금액표 검색·주장별 인용 개선 후 개발용 재비교다. 최종 20문항은 미실행이며 게시·Cloud 변경은 하지 않았다.

**최초 v3 개발용 평가 — 2026-10-19:** 평가 도구·v3 준비에서 **소프트웨어 테스트 409개**를 통과한 뒤 같은 구현으로 **개발용 20문항**의 실제 비교를 완료했다. 원본 AI 통과는 **청크 14/20·페이지 15/20**, 필수 인용 근거 전체 확보는 **10/16·12/16**이다. 실제 **답변 40회 + 채점 39회 = 모델 79회**를 호출했으며 페이지 인용 검증 실패 1건 외에 제공업체·채점 오류는 없었다. 오프라인 산출물 검사·보고서 재현을 통과했고 기준 파일 376개를 보존했다. 당시 평가에서는 소프트웨어 테스트를 반복하지 않았다. [결과·분석](Phase6_RetrievalAndAnswerQuality.md#v3-개발용-평가--2026-10-19), [보고서](../eval/results/v3_dev_20261019_1003/report.md), [검증](../eval/results/v3_dev_20261019_1003/verification.json)을 참고한다. 최초 결과는 그대로 보존했다. 과거 채점 복구는 실행하지 않았으며 이후 새 계획과 원래 채점기·버전의 호환을 함께 확인해야 한다.

[Phase 6 보고서](Phase6_RetrievalAndAnswerQuality.md)의 최초 구현 결과에 테스트 267개 통과, 선택형 pages/k=5의 개발용 필수 근거 전체 확보 32/32, 알려진 실제 사례 6건의 같은 모델 AI 채점 통과를 기록했다. 코드는 [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa)으로 푸시했다. 사용자는 Cloud에 pages/5/6000 설정을 적용하고 Reboot했다고 보고했으며 실제 실행 동작은 별도로 확인하지 않았다. 아래 기존 Phase 5 점검은 과거 증빙으로 보존한다.

**보존한 최종 평가:** 이전 [고정 20문항 실행](../eval/results/v3_closeout_20261019/report.md)은 필수 근거 12/16·내용 15/20·인용까지 13/20·답변 불가 보류 4/4·평균 5.193초다. 개발 6개와 최종 20개의 답변을 생성했고 별도 AI 채점은 없다. 이후 집중 보완으로 이 점수를 덮어쓰지 않는다. 앞뒤 날짜별 기록은 당시 상태이며 게시·평가 대기라는 과거 작업은 현재 완료 기록으로 대체한다.

## 프로젝트 목표와 증빙 우선순위

PDF 추출·청크 분할·임베딩·검색·문맥 구성·근거 기반 생성·출처 검증을 이해하고 구현했음을 설명한다. 필요한 근거와 올바른 답변을 얼마나 자주 얻는지 측정하고, 개선 이유와 남은 실패를 제시한다. Streamlit은 시연 화면이다. 실제 사용자 확보, 동시 접속 규모, UI 확장, 기업용 운영은 현재 완료 요건이 아니다.

이전 후속에서 추적 보강·기준 고정 비교·오프라인 감사·채점 복구 도구를 구현했고 당시 테스트 347개가 통과했다. 과거 근거 확보는 청크 37/48에서 페이지 47/48, 마지막 페이지 선택 개선 후 48/48로 늘었으나 해당 답변 채점은 미완료다. 새 v3 개발용 측정은 별도이며 과거 누락 채점을 복구한 것은 아니다. 추적은 답변이 나온 과정을 설명하고, 정답이 정해진 질문·채점 기준·검토는 답변 품질을 평가한다. 검색 근거 확보율, 답변 정확도, 근거 일치·조건 완전성, 적절한 보류를 나누어 보고한다. 프로그램 테스트·같은 모델 채점·사람 검토·최종 평가를 구분한다. 사용자는 2026-10-19 v3를 위해 API 사용을 재개했고 과거 87건은 이번 실행 대상에서 제외했다.

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

## 완료 상태와 선택적 후속

사용자가 제한한 마무리와 이후 개선 1·2·4번을 승인했다. 이 포트폴리오에 필수로 남은 개발·새 평가는 없다. 원래 실패와 미완료 검토는 보존한다.

| 상태 | 작업 | 결과 / 범위 |
| --- | --- | --- |
| 완료 | RAG 구현·추적·평가·데모 | Phase 1~6, 공개 URL, 로컬 실행의 원격 Trace, 고정 최종 보고서, 사용자 확인 기록 |
| 완료 | 1. 답변 필수 항목 | 실제 답변 7개 확인. 대상 계좌 관련 3개 답변에 계좌 확인 자료 명시 |
| 완료 | 2. 모든 근거 인용 | 서로 다른 주장 인용 전체 표시, 호환 유지, 저장 답변 화면 검사 통과 |
| 완료 | 4. 관측한 인용 누락 | 최종 4사례 Codex 원문 대조 통과. 이전 실패 보존, 최신 소프트웨어 테스트 488개 통과 |
| 게시 / 사용자 보고 | 배포 코드와 Cloud 설정 | [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4) 푸시, 사용자 보고 기준 4096토큰 설정 완료. 최신 게시본의 새 Cloud 답변·재시작은 별도로 관측하지 않음 |
| 선택 | 3. 복합 검색과 독립 검증 | 알려진 검색 누락은 남음. 독립 사람 채점을 했다고 주장하려면 해당 채점이 필요하나, 둘 다 포트폴리오 종료 조건은 아님 |
| 보류 / 별도 | 평가기 확장·과거 채점 87건·검토 34건·Phase 7·CI·서비스 운영 | 새 유료 실행 계획 없음. 동시 접속은 범위 밖 |

## 이전 작업 순서와 결정 사항 — 2026-10-16

**로컬 완료:** 추적 계층·토큰 기록 수정, pages/5/6000의 실제 원격 대조, 쌍별 답변 120회 시도 기록, 오프라인 산출물 검증, 채점 복구 준비, 검증 진단, 마지막 페이지 선택, 테스트 347개 통과. 과거 답변 비교의 필수 근거 확보는 청크 37/48·페이지 47/48이며 최신 검색만 비교한 선택 검사는 48/48이다. 과거 실행에서 검증을 통과한 응답은 59/60·57/60이다. AI 채점은 가능한 응답 중 15/59·14/57만 완료했다. 원본의 확인된 통과 개수 14/60을 정확도 비율로 해석하지 않는다.

**2026-10-16 당시 결정:** 충전과 잔여 AI 채점 87건을 보류했다. 이후 사용자가 2026-10-19 충전하고 다음 평가 단계를 진행했다. 복구 준비에는 API를 호출하지 않았으며 [과거 계획](../eval/results/phase6_review_recovery_selection_20261016/plan.json)은 저장된 성공 답변의 채점 실패 건을 대상으로 한다. 이후 코드·채점 프롬프트가 바뀌어 새 계획과 원래 채점기·버전의 호환을 함께 확인해야 한다. 해당 채점은 새 선택 방식이 아닌 이전 답변을 평가한다. 복구 중 제공업체 오류가 발생하면 첫 오류에서 멈추고 기존 결과를 보존한다.

당시 후속은 별도 enterprise-rag 체크아웃에서 게시를 준비했고 답변 프롬프트를 유지했다. 이후 2026-10-19 문맥 선택·생성 및 채점 지시·평가 도구를 개선했으며 합의한 최종 구현은 현재 [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4)으로 게시했다. 사용자 보고 기준 Cloud 설정과 검증한 로컬 실행을 구분하고 원래 최종 평가·사람 검토의 한계를 유지한다.

## 로컬 검증 재현

프로젝트 루트의 기존 환경에서 실행한다.

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement verify --output-dir eval/results/v3_refinement_dev_20261019
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/v3_dev_20261019_1003
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
| 2026-10-19 | 평가 도구 확장과 v3 준비 구현·테스트 409개 통과. 원본 데이터·보고서·실행 RAG 동작 유지. 다음은 명시적 API 재개 후 개발·최종 평가이며 이번에는 API 호출·게시하지 않았다. 별도 dev-log 미설치로 여기에 기록. |
| 2026-10-19 | API 사용 재개와 v3 개발용 평가 완료 기록. 모델 79회 호출, 원본 통과 14/20·15/20, 근거 확보 10/16·12/16. 산출물 검증·기준 파일 보존 완료. 채점 해석·문맥 선택·인용 생성 개선 후 코드 고정 최종 평가를 우선했다. 실행 코드 수정·게시 없음. dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 개발 개선·저장 답변 비교 완료. 테스트 439개, 새 모델 호출 59회, 근거 12/16→14/16·유효 출력 19/20→20/20이나 같은 기준 AI 통과는 17/20으로 동일. 파일 434개 보존. 채점 분리·논쟁 사례 검토·결재 표 검색·주장별 인용을 우선하고 최종 평가·게시 대기. dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 검토한 파일 192개를 8686fff로 게시한 뒤 채점 분리·규정 주제 선택을 로컬 구현했다. 테스트 483개, 개발용 근거 14/16→16/16·v2 48/48 유지. 실제 채점은 요청 10회·채택 6개 단계·검증 거부 3개·API 오류 1개로 부분 완료. 파일 522개 보존, 새 답변·최종 평가·독립 판정 대기. dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 제한한 마무리: 테스트 484개·생성 26회·별도 채점 없음, Codex 기준 최종 내용 15/20·인용까지 13/20. 시연 재생·재시작 통과, 원본 554개 보존. 사람 검토·게시 별도, 추가 평가기 개발 보류. dev-log 미설치. |
| 2026-10-19 | 완료한 개선·게시본 175bda7·테스트 488개·사용자의 Cloud 설정 보고를 반영했다. 필수 포트폴리오 작업은 완료하고 선택적 검색·독립 검토와 과거 결과를 구분했다. 문서만 변경, dev-log 미설치. |
