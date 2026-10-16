# Phase 6 — Retrieval and Answer Quality `✅ Local implementation · ⏸ AI grading`

> Improve complete evidence retrieval and condition-preserving answers with a bounded, auditable context.

**Started**: 2026-10-16 (Asia/Seoul)\
**Completed locally**: 2026-10-16\
**Status**: Local implementation/tests and real remote tracing verified. Comparison attempts completed; 87 failed AI reviews are deferred after confirmed API credit exhaustion and the user's decision not to recharge now. Cloud settings/reboot remain owner-reported, not independently verified.\
**Prerequisites**: Phases 1–4 implemented; Phase 5 demo deployed. The user explicitly deferred remaining Phase 5 checks and authorized Phase 6 documentation, development, and tests.\
**Technology**: Python 3.12, existing E5/Chroma/Claude stack, pytest.

## Latest user decision — 2026-10-16

The owner reported applying `RAG_RETRIEVAL_MODE="pages"`, `RAG_TOP_K=5`, and `RAG_CONTEXT_MAX_CHARS=6000` in Streamlit Community Cloud and rebooting the app. Record this as owner-reported completion of the settings action, not an independently verified Cloud test. The implementation was pushed to `main` as [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa).

**Project objective:** demonstrate understanding and implementation of RAG, measured answer accuracy, precise evidence/condition handling, and explainable improvements. The Streamlit app is a demonstration surface; production adoption and service operations are not the success criteria. Concurrent-user testing is excluded from the current scope, and Phase 7 usability remains deferred.

The user subsequently authorized development and testing for these evidence priorities and supplied a LangSmith key locally. Actual local-to-remote trace verification is now complete; the frozen 60-question comparison is recorded in the follow-up below. The 34-entry human-review queue and fresh independent evaluation remain pending. Cloud resource checks, CI, and enterprise expansion are optional later work. Runtime defaults remain unchanged; the agent did not edit local `.env`. The [activation procedure](../DEPLOYMENT.md#phase-6-page-context-activation) remains available for reference.

`pages/5` was selected from the four tested configurations because it matched `pages/7` on development evidence coverage with less context. The 6,000-character budget was fixed before comparison; different budgets were not optimized, and universal optimality is not claimed. Source hashes and historical evaluation reports remain unchanged.

## Scope and tasks

| Task | Work | Acceptance criteria | Verification | Status |
| --- | --- | --- | --- | --- |
| 6.1 | Add an opt-in page-context retrieval mode beside existing chunk retrieval | One vector search; distinct source pages; bounded context; unchanged original page text and accurate source metadata; existing index/bundle reusable | Retrieval, provenance, budget, configuration, and compatibility tests | ✅ |
| 6.2 | Compare existing k=3 and k=5 with bounded page-context candidates | Save full retrievals, configuration, coverage, context size, timing, and failures; never pass reference answers into retrieval | Real local E5 search on the 40 development questions; no generation needed | ✅ 160 searches |
| 6.3 | Strengthen required-item and condition/timing coverage in the answer instruction | Preserve abstention, strict quote checking, and at most one generation; no reference/rubric leakage | Grounding/RAG tests and a small explicit live smoke run if local API access is available | ✅ Six answers and six AI reviews |
| 6.4 | Record results and integrate documentation | English/Korean Phase report and README links; distinguish software tests, retrieval metrics, live observations, and deferred evaluation | Existing full pytest suite, saved Phase 5 artifact verification, deployment bundle check | ✅ 267 tests |

## Design fixed before comparison

- Original local implementation scope: preserve default chunk retrieval (k=3), the deployed configuration, PDFs, embeddings, index bundle, and historical Phase 5 results. Cloud activation was excluded from that completed scope; the later user decision above authorizes it separately.
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

Retrieval coverage is not answer correctness. The independent contributions of larger candidate pools, page expansion, and prompt changes were not separately measured. At the original implementation checkpoint, broader answer evaluation and real tracing were still pending; the later follow-up below supersedes that status. A fresh holdout and human review remain pending. Demo UX, enterprise upload/authentication, and broad operational changes belong to later scope.

## Follow-up implementation — 2026-10-16 `Implemented; grading partly deferred`

The user now requested implementation and tests for the RAG evidence priorities. Keep the UI and concurrent-user work deferred. This follow-up does not change retrieval or answer instructions to fit observed evaluation answers.

| Task | Implementation | Completion evidence | Status |
| --- | --- | --- | --- |
| 6.5 | Add explicit retrieval-mode/context settings and generation token usage to traces; validate remote question, context, prompt, output, hierarchy, and settings | SDK payload and mismatched/partial-remote-trace tests; actual pages/5/6000 remote readback | ✅ Verified; local execution and remote service, not the Cloud app |
| 6.6 | Freeze and run a paired current-code comparison: chunks/k=5 versus pages/k=5, both with the current answer prompt and 6,000-character page budget | Immutable protocol/source/document/dataset fingerprints; all 60 known v2 questions; at most 120 answer calls plus 120 separate same-model AI reviews; durable progress and no implicit repeats | 120 answer attempts; 29 grades completed, 87 errors deferred, 4 skipped |
| 6.7 | Derive an auditable quality report with full denominators, paired gains/regressions, and separate evidence/answer/judge diagnostics | Offline recomputation and tamper/missing-record tests; raw attempts preserved; human review remains pending | ✅ Offline audit/report and recovery plan; complete accuracy remains unknown |

Both configurations use chunk size 800/overlap 120, the same model, and the current prompt. The comparison measures the combined page-mode retrieval change, including its larger candidate pool; it does not isolate every component or compare old versus new prompts. All 60 questions are known; even rows originally labeled `final` are regression cases here, not a fresh holdout. The 6,000-character bound is fixed, not optimized. Preserve the 90 existing evaluation files and use a new output directory. Freeze code before live evaluation; errors and missing results stay in denominators. Remote tracing and evaluation are distinct checks; neither substitutes for human grading.

### Follow-up implementation and reproducibility

- `tracing.py` records structured model messages, `ls_provider`/`ls_model_name`, retrieval settings, and token usage. Cache creation/read tokens are included in normalized input totals. Errors retain only their type; keys and client objects are excluded.
- Real remote verification exposed a missing `parent_run_id` on child completion PATCH requests. The server treated the update as a root run and rejected its two-part `dotted_order`. Completion requests now preserve the parent; the actual SDK payload test checks this field. Five-second connection/read limits replace the too-short one-second setting; retries remain disabled.
- `eval.check_trace --preflight` checks configuration without clients or requests. The live command generates once, preserves its answer, and reads the remote record up to three times. It checks actual context, reconstructed prompt, validated output, settings, token counts, completion and parent relationships. Private trace files remain ignored by Git.
- The successful real trace is saved in local `data/trace_check_phase6_20261016_v3.json`. It used 4,134 context characters and 5,887 input / 166 output tokens. Earlier unsuccessful trace checks remain in the two preceding files; three answers were generated in total while debugging. Transport-only diagnostic records are marked `diagnostic_only` and are not evaluation results. The user supplied the key; the checker enabled tracing only in its process.
- `eval/quality.py` freezes the protocol before paid calls and writes each attempt as pending before invoking the model. Completed attempts are reused only with explicit `--resume`; ambiguous/pending attempts stop the run. No automatic retry improves a score or hides a failure. Answers run sequentially in alternating configuration order; two workers handle separate AI reviews, not app concurrency testing.
- Offline verification checks individual and aggregate hashes, exact question/answer links, citations, evidence checks, judge inputs and raw grades. It preserves manual report edits and historical review notes. A hash proves consistency, not semantic correctness.

```powershell
# New output directory; existing index and cached E5 model required. No model calls.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality freeze --output-dir eval/results/quality_new_run
# Billable: up to 120 answers and 120 separate AI reviews; no automatic retries.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality run --output-dir eval/results/quality_new_run
# Offline verification and reproducible report. No API keys needed.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/quality_new_run
.\.venv\Scripts\python.exe -X utf8 -m eval.quality report --output-dir eval/results/quality_new_run
```

The new tests cover interrupted-attempt protection, source drift before API calls, mismatched or duplicate records, raw judge consistency, full denominators, paired regressions, and preservation of human edits. **297 tests passed in 82.93 seconds** after the tracing/evaluator changes; the focused trace/evaluator run passed 44 tests. `pip check`, the historical 120-answer/120-review verifier, and the 22-chunk deployment-bundle check also passed. No dependencies or runtime retrieval/prompt rules were added or changed in this follow-up.

### Follow-up results and remaining work

Evidence: [protocol](../eval/results/phase6_quality_20261016/protocol.json), [all attempts](../eval/results/phase6_quality_20261016/answers.json), [raw derived report](../eval/results/phase6_quality_20261016/report.md), [verification/status](../eval/results/phase6_quality_20261016/verification.json), [offline recovery plan](../eval/results/phase6_review_recovery_20261016/plan.json).

| Observed metric | chunks/5 | pages/5 |
| --- | ---: | ---: |
| Complete required quotes in context | 37/48 | 47/48 |
| Evidence groups recovered | 62/75 | 74/75 |
| Required pages for multi-document questions | 13/18 | 17/18 |
| Validated responses returned, including abstentions | 59/60 | 57/60 |
| Unanswerable-question abstention contract | 12/12 | 12/12 |
| Successful AI reviews / eligible responses | 15/59 | 14/57 |
| Mean context characters | 3,153.40 | 4,222.52 |
| Mean successful RAG time | 4.02 seconds | 4.09 seconds |

**Complete answer accuracy is not established.** The 120 grading records contain 29 successes, 87 `ClaudeError` records, and 4 skipped reviews after RAG validation errors. A separate minimal diagnostic confirmed HTTP 400 with insufficient credit; model-access lookup still succeeded. The user chose **not to recharge and to defer the remaining 87 reviews**. No further live calls followed that decision. The raw report's 14/60 confirmed AI passes in each mode must not be presented as 23.3% answer accuracy. Only 14 pairs have valid grades in both modes; their q08 gain does not establish whole-set improvement.

The following findings motivated the diagnostics/selection work completed below:

1. **Selection:** q51 requires the account-change clause on `04_contract_settlement.pdf`, page 3. It is rank 9 among 15 candidates but outside the final five pages. Context uses only 4,031 characters, so increasing the character budget alone would not fix it. Compare evidence selection/reranking or question decomposition in a later frozen experiment.
2. **Failure details:** chunks/q56 and pages/q25/q30/q56 were rejected by `AnswerValidationError`. Context and usage survive, but the original evaluator did not retain invalid raw output or the exact violated rule. Add safe failure-detail capture before guessing at prompt changes; keep strict citation checks.
3. **Interpretation:** q31's chunk answer abstains, while the page answer includes receipt + 3 business days for inspection and inspection completion + 5 business days for asset numbering. q54 page output preserves emergency prior security confirmation. These inspected examples are not completed AI/human grades for those rows.

After freezing the comparison, `eval/recover_reviews.py` was added. Offline `prepare` selects failed AI reviews on successful saved answers. `run` never generates RAG answers, preserves originals, stops on the first failed review, and records only allowlisted provider-error categories. `--resume` reuses successes without repeating failed calls; a new plan with `--carry-from` retains previous successes after a provider failure. Eight offline recovery tests and the final **305-test suite (67.05 seconds)** passed. The 87-item plan is prepared; **its live run was not executed**.

```powershell
# Future execution only after the owner resumes grading and funds API access.
.\.venv\Scripts\python.exe -X utf8 -m eval.recover_reviews run --output-dir eval/results/phase6_review_recovery_selection_20261016
# After recovery execution; offline validation only.
.\.venv\Scripts\python.exe -X utf8 -m eval.recover_reviews verify --output-dir eval/results/phase6_review_recovery_selection_20261016
```

All 90 pre-existing evaluation files are preserved. Historical human review (34 entries) remains deferred; fresh independent questions are still needed for generalization claims. UI remains deferred and concurrency testing excluded. These follow-up changes are local, not committed/pushed.

### Validation diagnostics and evidence selection

The owner approved these two improvements. All work in this iteration is offline: no answer generation, AI grading, remote trace requests, or recharge. Preserve existing answers, grades, and the original recovery plan; source changes require a newly prepared offline recovery plan before later grading.

- **Validation diagnostics:** retain a stable rule code and JSON field location for the first rejected rule, plus safe response length/hash metadata. Keep strict rejection, one generation attempt, and generic UI errors. The added diagnostics exclude rejected text and arbitrary exception messages; existing opt-in generation tracing is unchanged. Four historical errors lack raw output and exact rule details; mark their causes unavailable instead of inferring them.
- **Page selection:** keep the first four fitting pages at k=5. Use the final slot for a candidate that adds weighted question-term coverage while retaining every query feature uniquely provided by the old final page. Use character pairs for Korean inflections and case-folded words elsewhere; weights depend only on candidate-page frequencies. Preserve vector order on ties, page/source integrity, the 6,000-character budget, and one vector search. No reference answer or evidence annotation enters selection.
- **Verification:** compare both selectors on identical candidate lists from one local search per known question. Only 57 original rows retained candidates; check those lists and all 60 original contexts for agreement. Publish gained/lost evidence cases, context size, candidate versus final-context coverage, and q51 provenance. Add synthetic rule/selection/negative-control tests and run the full suite. Retrieval improvement alone does not establish answer accuracy.

**Completed locally: 347 tests passed in 18.36 seconds.** The 42 new tests cover rule locations, secret-safe diagnostics, no retry, both evaluation runners, trace error metadata, budget/fallback behavior, preserved query features, annotation isolation, and report tampering. Existing Phase 5/6 artifact verifiers and the 22-chunk deployment-bundle check passed. All 336 evaluation files present before this iteration remain byte-identical. No live model or remote trace calls were made.

`AnswerValidationError.diagnostic()` now exposes `rule`, `path` (a JSON pointer), and an allowlisted description. For example, `quote_not_in_source` at `/claims/1/evidence/0/quote` identifies the first citation in the second claim; this is an illustration, not a diagnosis of an old failure. `RAGAssistant` adds `validation_error` and `response_metadata` (length/SHA-256) to its failure record. Both evaluation runners retain them; the LangSmith root error also carries the rule/path when tracing is enabled. Response rejection, the answer prompt, and the one-generation limit are unchanged. The four historical errors remain explicitly **unavailable in the original record**, with no invented cause or regeneration.

`PageContext` uses `rank_with_coverage_slot_v1` in page mode when the runtime passes the question. It preserves the first k−1 fitting pages and considers a replacement for the final slot. A replacement must retain all query features that only the old final page supplied and strictly add weighted uncovered features. Features are Korean character pairs or case-folded words; rarer candidate-page features receive more weight. Ties preserve rank. Scoring uses the text that actually fits, including a whole-seed fallback; unsent page tails cannot earn coverage. `seed_rank`, `replaced_seed_rank`, and `selection_reason` explain a change. This is a conservative lexical heuristic, not proof of semantic completeness. Chunk mode, index contents, source integrity, and page/character limits remain unchanged; no new setting or dependency is required.

| Offline search metric | Original page selection | New page selection |
| --- | ---: | ---: |
| Complete required quotes in context | 47/48 | 48/48 |
| Evidence groups | 74/75 | 75/75 |
| Complete multi-document page coverage | 17/18 | 18/18 |
| Mean context characters | 4,222.52 | 4,233.82 |
| Maximum context characters | 4,708 | 4,559 |

All 57 preserved candidate lists and all 60 original contexts reproduced. The same candidates were used on both sides; candidates already contained all 48 answers' required evidence. Context changed for 32/60 questions, with one complete-evidence gain (q51) and no lost complete-evidence cases. q51 retains its first four sources and replaces the fifth page with `04_contract_settlement.pdf` page 3, from candidate rank 9. Context falls from 4,031 to 3,801 characters. **This is known-case retrieval coverage, not 100% answer accuracy.** No new answer, AI grade, human review, or unseen test was performed.

Evidence: [comparison and historical error audit](../eval/results/phase6_selection_20261016/comparison.json), [frozen protocol](../eval/results/phase6_selection_20261016/protocol.json), [test/verification record](../eval/results/phase6_selection_20261016/verification.json). Source changes make the original prepared recovery plan stale by design. It remains intact; the [new offline plan](../eval/results/phase6_review_recovery_selection_20261016/plan.json) targets the same 87 old answers and passes its current-source check. Recovering those grades later evaluates the old saved answers, not this new selector. Charging/grading remain deferred, and neither recovery plan was executed.

```powershell
# Offline reproduction using the installed local embedding model; use a new directory.
.\.venv\Scripts\python.exe -X utf8 -m eval.selection compare --source-dir eval/results/phase6_quality_20261016 --output-dir eval/results/selection_new_run
# Offline audit of the recorded comparison; no model calls.
.\.venv\Scripts\python.exe -X utf8 -m eval.selection verify --output-dir eval/results/phase6_selection_20261016
```

This revision packages these completed local changes for GitHub publication; Cloud runtime verification remains deferred. The next quality work is preparing fresh independent questions; later live answers should confirm diagnostic capture and the new selector's answer quality when the owner resumes API use. Usability remains deferred and concurrency testing excluded.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-16 | Created the implementation plan before code changes. User authorized development and tests. Separate dev-log skill unavailable; history is maintained here. |
| 2026-10-16 | Implemented opt-in bounded page retrieval and item/condition-preserving answer instructions; selected pages5 on development retrieval, completed 267 tests and six live/AI-reviewed cases, linked evidence and both READMEs. Local scope complete; no Cloud publishing. |
| 2026-10-16 | Recorded successful code publication as b89ed76 and the user's decision to activate pages/5/6000 first while deferring Phase 7 usability. Prepared Cloud Settings instructions; server values and activation are unverified because no connected Cloud administration tool is available. Documentation only; separate dev-log unavailable. |
| 2026-10-16 | Recorded the owner's settings/reboot completion report and clarified the RAG demonstration objective: logic, measured accuracy, precise evidence, and explained improvements. Excluded concurrency testing; kept usability deferred. Prioritized tracing/evaluation proposals without executing new remote checks. Separate dev-log unavailable; history recorded here. |
| 2026-10-16 | Completed trace metadata/readback fixes, verified real LangSmith, ran the frozen 120-answer comparison, diagnosed partial grading and insufficient credit, and prepared 87 review recoveries offline. Owner deferred charging/grading. Final 305 tests passed; historical 90 artifacts preserved. Local changes only; separate dev-log unavailable. |
| 2026-10-16 | Added safe validation-rule/path records and conservative final-page selection; offline coverage improved 47/48 to 48/48 with no complete-evidence regressions. 347 tests passed, 336 artifacts preserved, and an updated 87-review plan prepared without execution. No model calls, push, or Cloud change; dev-log unavailable. |

---

# Phase 6 — 검색·답변 품질 개선 `✅ 로컬 구현 · ⏸ AI 채점`

> 길이를 제한하고 근거를 추적할 수 있는 문맥으로 필수 근거 검색과 조건을 보존하는 답변을 개선한다.

**시작일**: 2026-10-16 (한국 시간)\
**로컬 완료일**: 2026-10-16\
**상태**: 로컬 구현·테스트 및 실제 원격 추적 검증 완료. 확대 비교 시도는 완료했으나 API 잔액 부족 확인 후 사용자가 충전하지 않고 AI 채점 실패 87건을 보류하기로 했다. Cloud 설정·Reboot는 사용자 보고 기준이며 실제 동작은 별도 검증하지 않았다.\
**선행 조건**: Phase 1~4 구현, Phase 5 데모 배포. 사용자가 남은 Phase 5 검증을 보류하고 Phase 6 문서·개발·테스트를 명시적으로 요청했다.\
**기술 구성**: Python 3.12, 기존 E5/Chroma/Claude, pytest.

## 최신 사용자 결정 — 2026-10-16

사용자가 Streamlit Community Cloud에 `RAG_RETRIEVAL_MODE="pages"`, `RAG_TOP_K=5`, `RAG_CONTEXT_MAX_CHARS=6000`을 적용하고 앱을 Reboot했다고 보고했다. 설정 작업은 사용자 보고 기준 완료로 기록하며 별도의 Cloud 테스트 통과로 간주하지 않는다. 구현 코드는 [b89ed76](https://github.com/SoyeonAhn3/enterprise-rag/commit/b89ed76b615a02c13c5e9ce80928a4ae9bcdadaa)으로 `main`에 푸시했다.

**프로젝트 목표:** RAG 원리를 이해하고 직접 구현했으며, 답변 정확도를 측정하고, 근거·조건을 정교하게 처리하며, 개선 이유를 설명할 수 있음을 보여준다. Streamlit 앱은 시연 수단이며 실제 사용자 확보나 서비스 운영을 성공 기준으로 삼지 않는다. 동시 접속 검사는 현재 범위에서 제외하고 Phase 7 사용성은 계속 보류한다.

사용자가 이후 RAG 증빙 중심의 개발·테스트를 요청하고 로컬에 LangSmith 키를 입력했다. 실제 로컬 실행과 원격 추적 대조를 완료했으며, 조건을 고정한 60문항 비교는 아래 후속 작업에 기록한다. 사람 검토 34건과 새 독립 평가는 대기 중이다. Cloud 자원 검사·CI·기업용 확장은 선택적인 후속 작업으로 둔다. 실행 기본값은 유지하며 에이전트는 로컬 `.env`를 수정하지 않았다. [활성화 절차](../DEPLOYMENT.md#phase-6-페이지-문맥-활성화)는 참고용으로 보존한다.

`pages/5`는 비교한 네 설정 중 개발용 근거 확보 성적이 `pages/7`과 같으면서 문맥이 적어 선택했다. 6,000자 한도는 비교 전에 정한 값이며 여러 한도를 비교해 최적화한 결과는 아니다. 모든 문서·질문에서 최적이라는 주장도 하지 않는다. 소스 해시와 과거 평가 기록은 그대로 보존한다.

## 범위와 Task

| Task | 작업 | 완료 기준 | 검증 방법 | 상태 |
| --- | --- | --- | --- | --- |
| 6.1 | 기존 청크 검색에 선택 가능한 페이지 문맥 검색 추가 | 벡터 검색 1회, 중복 페이지 제거, 문맥 길이 제한, 원래 페이지 본문·출처 보존, 기존 인덱스·번들 재사용 | 검색·출처·길이 제한·설정·호환성 테스트 | ✅ |
| 6.2 | 기존 k=3·k=5와 페이지 문맥 후보 비교 | 전체 검색 결과·설정·근거 포함률·문맥 길이·시간·실패 저장. 참고 정답은 검색에 전달하지 않음 | 개발용 40문항의 실제 로컬 E5 검색. 답변 생성 불필요 | ✅ 검색 160회 |
| 6.3 | 요구 항목과 조건·시점을 보존하는 답변 지시 보강 | 보류 원칙·엄격한 원문 인용 검사·최대 생성 1회 유지. 참고 정답·채점 기준 유출 없음 | Grounding/RAG 테스트와 로컬 API가 사용 가능할 때 소수 실제 답변 검사 | ✅ 답변·별도 AI 채점 각 6회 |
| 6.4 | 결과 기록과 문서 연결 | 영문·국문 Phase 및 README 링크. 프로그램 테스트·검색 지표·실제 답변 관찰·보류 평가 구분 | 기존 전체 pytest, Phase 5 저장 산출물 검증, 배포 번들 검사 | ✅ 테스트 267개 |

## 비교 전에 정한 설계

- 최초 로컬 구현 범위는 기본 청크 검색(k=3), 배포 설정, PDF, 임베딩, 인덱스 번들, Phase 5 과거 결과를 보존하는 것이었다. 완료된 당시 범위에서 Cloud 활성화는 제외했으며, 위의 후속 사용자 결정으로 별도 진행을 승인받았다.
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

검색 근거 포함률은 답변 정답률이 아니다. 후보 수 확대·페이지 확장·프롬프트 변경의 개별 기여는 분리 측정하지 않았다. 최초 구현 완료 시점에는 광범위한 답변 평가와 실제 추적이 대기 중이었으며, 아래 후속 기록으로 상태를 갱신한다. 새 독립 평가셋과 사람 검토는 대기 중이다. 데모 사용성, 기업용 업로드·인증, 광범위한 운영 변경은 이후 범위다.

## 후속 구현 — 2026-10-16 `구현 완료·AI 채점 일부 보류`

사용자가 RAG 증빙 중심의 개발과 테스트를 새로 요청했다. UI와 동시 접속 작업은 계속 보류한다. 이번 후속 작업에서는 관측한 평가 답에 맞춰 검색 로직이나 답변 지시를 수정하지 않는다.

| Task | 구현 | 완료 근거 | 상태 |
| --- | --- | --- | --- |
| 6.5 | 추적에 검색 방식·문맥 설정·생성 토큰 사용량 추가. 원격 질문·문맥·프롬프트·출력·계층·설정 대조 | SDK 전송 및 원격 기록 불일치·누락 테스트. 실제 pages/5/6000 원격 재조회 | ✅ 로컬 실행과 원격 서비스 검증. Cloud 앱 검증과 구분 |
| 6.6 | 현재 코드의 chunks/k=5와 pages/k=5 비교를 고정·실행. 같은 답변 프롬프트와 페이지 본문 6,000자 한도 사용 | 프로토콜·소스·문서·질문 해시 고정. 알려진 v2 60문항 전체. 답변 최대 120회 및 같은 모델의 별도 AI 채점 최대 120회. 중간 저장·암묵적 재시도 금지 | 답변 120회 시도·채점 성공 29·오류 87건 보류·미실행 4 |
| 6.7 | 전체 분모·개선 및 악화 쌍·근거/답변/채점 진단을 분리한 품질 보고서 | 오프라인 재계산·변조·누락 검사. 원본 시도 보존. 사람 검토는 대기 유지 | ✅ 오프라인 감사·보고서·복구 계획. 전체 정확도 미확정 |

두 설정은 청크 800자·중복 120자, 같은 모델과 현재 프롬프트를 사용한다. 비교는 검색 후보 수 증가를 포함한 페이지 모드의 묶음 효과이며 각 요소나 과거/현재 프롬프트의 효과를 분리하지 않는다. 60문항은 모두 알려진 문제이므로 원래 `final`로 표시한 행도 이번에는 회귀 사례이며 새 독립 평가가 아니다. 6,000자 한도는 고정하고 최적화하지 않는다. 기존 평가 파일 90개를 보존하고 새 출력 폴더를 사용한다. 실제 평가 전에 코드를 고정하고 오류·누락을 분모에 남긴다. 원격 추적과 답변 평가는 별도 검사이며 사람 채점을 대신하지 않는다.

### 후속 구현과 재현 방법

- `tracing.py`에 모델 메시지 구조, `ls_provider`/`ls_model_name`, 검색 설정, 토큰 사용량을 기록한다. 캐시 생성·읽기 토큰도 정규화한 입력 합계에 포함한다. 오류는 종류만 기록하며 키·클라이언트 객체는 제외한다.
- 실제 원격 검증에서 하위 실행 완료 PATCH에 `parent_run_id`가 빠진 문제를 발견했다. 서버가 해당 요청을 루트로 판단하여 두 부분으로 된 `dotted_order`를 거절했다. 완료 요청에도 상위 실행 ID를 유지하고 SDK 전송 테스트에서 검사한다. 짧았던 연결·읽기 제한은 1초에서 5초로 늘렸고 자동 재시도는 하지 않는다.
- `eval.check_trace --preflight`는 클라이언트·요청 없이 설정만 검사한다. 실제 명령은 답변을 한 번 생성해 보존하고 원격 기록을 최대 3회 조회한다. 실제 문맥, 재구성한 프롬프트, 검증한 출력, 설정, 토큰 수, 완료·상하위 관계를 대조한다. 비공개 추적 파일은 Git에서 제외한다.
- 성공한 실제 기록은 로컬 `data/trace_check_phase6_20261016_v3.json`에 있다. 문맥 4,134자, 입력/출력 토큰 5,887/166을 사용했다. 앞선 실패 2회도 이전 파일에 남아 있으며 수정 확인 과정에서 답변은 총 3회 생성했다. 전송만 확인한 진단 기록은 `diagnostic_only`로 표시하고 평가 결과에 포함하지 않는다. 사용자가 키를 입력했고 검증 명령 프로세스에서만 추적을 켰다.
- `eval/quality.py`는 과금 전에 프로토콜을 고정하고, 각 모델 호출 직전에 pending 시도를 저장한다. 완료한 시도는 명시적 `--resume`에서만 재사용하며 중단·불명확한 시도는 실행을 멈춘다. 자동 재시도로 점수를 높이거나 실패를 숨기지 않는다. 답변은 설정 순서를 번갈아 순차 실행하고 AI 채점만 작업자 2개로 처리한다. 앱 동시 접속 검사가 아니다.
- 오프라인 검증은 개별·집계 해시, 질문·답변 연결, 인용, 근거 확인값, 채점 입력과 원문 판정을 다시 검사한다. 사람이 수정한 보고서와 기존 검토 메모를 보호한다. 해시는 기록의 일관성을 확인하며 의미상 정답을 보증하지 않는다.

```powershell
# 새 출력 폴더, 기존 인덱스와 E5 모델 캐시 필요. 모델 호출 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality freeze --output-dir eval/results/quality_new_run
# 과금: 답변 최대 120회 + 별도 AI 채점 최대 120회. 자동 재시도 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality run --output-dir eval/results/quality_new_run
# API 키 없이 오프라인 검증·보고서 재현.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/quality_new_run
.\.venv\Scripts\python.exe -X utf8 -m eval.quality report --output-dir eval/results/quality_new_run
```

추가 테스트는 중단된 요청 재호출 방지, API 호출 전 코드 변경 차단, 불일치·중복 기록, 채점 원문과 판정 일치, 전체 분모, 쌍별 악화, 사람 메모 보존을 확인한다. 추적·평가 도구 구현 후 **전체 테스트 297개·82.93초 통과**했으며 관련 추적·평가 테스트는 44개 통과했다. `pip check`, 과거 답변·채점 각 120건 검증, 청크 22개 배포 번들 검사도 통과했다. 이번 후속에서 새 의존성을 추가하거나 검색·답변 프롬프트 규칙을 변경하지 않았다.

### 후속 결과와 남은 작업

증빙: [프로토콜](../eval/results/phase6_quality_20261016/protocol.json), [전체 시도](../eval/results/phase6_quality_20261016/answers.json), [원본 집계 보고서](../eval/results/phase6_quality_20261016/report.md), [검증·상태](../eval/results/phase6_quality_20261016/verification.json), [오프라인 복구 계획](../eval/results/phase6_review_recovery_20261016/plan.json).

| 관측 지표 | chunks/5 | pages/5 |
| --- | ---: | ---: |
| 필수 근거 원문 전체 포함 | 37/48 | 47/48 |
| 근거 그룹 확보 | 62/75 | 74/75 |
| 다중 문서 질문의 필수 페이지 포함 | 13/18 | 17/18 |
| 검증을 통과한 응답 반환, 보류 포함 | 59/60 | 57/60 |
| 답변 불가 질문의 보류 형식 준수 | 12/12 | 12/12 |
| AI 채점 성공 / 채점 가능한 응답 | 15/59 | 14/57 |
| 평균 문맥 글자 수 | 3,153.40 | 4,222.52 |
| 성공 응답 평균 RAG 시간 | 4.02초 | 4.09초 |

**전체 답변 정확도는 확정하지 않는다.** 채점 기록 120개는 성공 29건, `ClaudeError` 87건, RAG 검증 오류 후 미실행 4건이다. 별도 최소 진단에서 HTTP 400·API 잔액 부족 응답을 확인했으며 모델 접근 조회는 성공했다. 사용자는 **지금은 충전하지 않고 남은 채점 87건을 보류**하기로 했다. 그 결정 이후 추가 실제 호출은 하지 않았다. 원본 보고서의 설정별 AI 통과 14/60은 확인된 통과 개수이며 답변 정확도 23.3%라는 뜻이 아니다. 양쪽 모두 유효한 채점을 받은 질문은 14쌍뿐이므로 그 안의 q08 개선으로 전체 개선을 단정하지 않는다.

다음 관측 결과를 바탕으로 아래의 검증 진단·근거 선택 개선을 완료했다.

1. **근거 선택:** q51에는 `04_contract_settlement.pdf` 3쪽의 계좌 변경 조항이 필요하다. 후보 15개 중 9위에 있지만 최종 5개 페이지에서 빠졌다. 문맥은 4,031자뿐이므로 글자 한도만 늘려서는 해결되지 않는다. 이후 조건을 고정한 실험에서 근거 재정렬이나 질문을 나눠 검색하는 방법을 비교한다.
2. **실패 상세:** chunks/q56, pages/q25·q30·q56은 `AnswerValidationError`로 거절됐다. 문맥·토큰은 보존했지만 기존 평가기는 잘못된 원본 출력과 위반한 세부 규칙을 남기지 않았다. 프롬프트를 추측으로 바꾸기 전에 실패 상세를 안전하게 기록하고 엄격한 인용 검사는 유지한다.
3. **결과 해석:** q31 청크 답변은 보류했고 페이지 답변은 검수 등록을 수령 후 3영업일, 자산번호 부여를 검수 완료 후 5영업일로 구분했다. q54 페이지 답변은 긴급 상황에도 보안 사전 확인이 필요함을 보존했다. 답변을 살펴본 사례이며 해당 행의 AI·사람 채점 완료를 뜻하지 않는다.

고정 비교 후 `eval/recover_reviews.py`를 추가했다. 오프라인 `prepare`는 성공한 저장 답변 중 AI 채점 실패 건만 고른다. `run`은 RAG 답변을 다시 생성하지 않고 원본을 보존하며 첫 채점 오류에서 멈춘다. 제공업체 오류는 허용한 분류만 기록한다. `--resume`은 성공 결과를 재사용하되 실패 호출을 반복하지 않으며, 제공업체 오류 뒤에는 새 계획의 `--carry-from`으로 성공분을 이어받는다. 복구 테스트 8개와 최종 **전체 테스트 305개(67.05초)**가 통과했다. 87건 계획만 준비했고 **실제 복구 실행은 하지 않았다**.

```powershell
# 사용자가 채점을 재개하고 API 잔액을 확보한 뒤에만 실행.
.\.venv\Scripts\python.exe -X utf8 -m eval.recover_reviews run --output-dir eval/results/phase6_review_recovery_selection_20261016
# 복구 실행 후 API 호출 없이 저장 결과 검증.
.\.venv\Scripts\python.exe -X utf8 -m eval.recover_reviews verify --output-dir eval/results/phase6_review_recovery_selection_20261016
```

기존 평가 파일 90개를 보존했다. 사람 검토 34건은 계속 보류하며 일반화 성능을 주장하려면 새 독립 질문도 필요하다. 사용성은 보류, 동시 접속 검사는 범위 제외다. 이번 후속 변경은 로컬에 있고 아직 커밋·푸시하지 않았다.

### 검증 진단과 근거 선택

사용자가 두 개선을 승인했다. 이번 작업은 오프라인으로 진행한다. 답변 생성·AI 채점·원격 추적 요청·충전은 하지 않는다. 기존 답변·채점·복구 계획을 보존하며, 소스 변경 후에는 나중에 채점을 재개하기 전에 새 복구 계획을 오프라인으로 준비한다.

- **검증 진단:** 처음 위반한 규칙의 고정 코드와 JSON 필드 위치, 안전한 응답 길이·해시를 남긴다. 엄격한 거절·생성 1회·일반적인 화면 오류는 유지한다. 추가한 오류 진단에는 거절된 원문과 임의의 예외 메시지를 넣지 않으며, 기존 선택형 생성 추적의 동작은 유지한다. 과거 오류 4건은 원문과 상세 규칙이 없어 원인을 알 수 없음으로 표시하고 추측하지 않는다.
- **페이지 선택:** k=5에서 먼저 들어간 네 페이지를 유지한다. 마지막 한 칸은 기존 마지막 페이지만 제공하던 질문 특징을 모두 보존하면서 질문의 다른 표현도 추가로 담는 후보에 배정한다. 한국어는 두 글자 묶음, 그 외는 대소문자를 통일한 단어를 사용하며 후보 페이지의 등장 빈도로 가중치를 정한다. 동점이면 검색 순위, 페이지·출처 무결성, 6,000자 한도, 벡터 검색 1회를 유지한다. 참고 정답·근거 주석은 선택 코드에 전달하지 않는다.
- **검증:** 알려진 60문항을 각각 로컬에서 한 번 검색하고 같은 후보로 기존·새 선택 방식을 비교한다. 원래 후보가 남은 57건과 원래 문맥 60건의 일치를 확인한다. 근거 확보 개선·악화 사례, 문맥 길이, 후보와 최종 문맥의 확보율, q51 출처를 공개한다. 인위적으로 만든 오류·선택·부정 사례 테스트와 전체 테스트를 수행한다. 검색 개선만으로 답변 정확도가 향상됐다고 판단하지 않는다.

**로컬 완료: 전체 테스트 347개가 18.36초에 통과했다.** 새 테스트 42개는 규칙·발생 위치, 비밀값을 넣지 않는 진단, 재시도 방지, 평가기 두 종류, 추적 오류 기록, 글자 한도·청크 대체, 질문 표현 보존, 정답 주석 분리, 보고서 변조를 확인한다. 기존 Phase 5·6 산출물 검증과 청크 22개 배포 번들 검사도 통과했다. 이번 작업 전에 있던 평가 파일 336개는 바이트 단위로 보존했다. 실제 모델·원격 추적 호출은 하지 않았다.

`AnswerValidationError.diagnostic()`는 `rule`, `path`(JSON 필드 위치), 허용한 고정 설명을 반환한다. 예를 들어 `quote_not_in_source`와 `/claims/1/evidence/0/quote`는 두 번째 주장에 있는 첫 인용이 원문에 없다는 뜻이다. 이는 설명용 예시이며 과거 오류를 진단한 결과가 아니다. `RAGAssistant`는 실패 기록에 `validation_error`와 `response_metadata`(길이·SHA-256)를 남긴다. 평가기 두 종류가 이를 저장하며 추적을 켜면 LangSmith 루트 오류에도 규칙·위치를 남긴다. 엄격한 응답 거절, 답변 프롬프트, 최대 생성 1회는 그대로다. 과거 오류 4건은 **원본 기록에 상세 정보가 없음**으로 명시했으며 원인을 만들어 내거나 답변을 다시 생성하지 않았다.

페이지 모드에서 질문을 전달받은 `PageContext`는 `rank_with_coverage_slot_v1`을 사용한다. 먼저 들어간 k−1개 페이지를 유지하고 마지막 한 칸의 교체만 검토한다. 기존 마지막 페이지에서만 확보하던 질문 표현을 모두 보존하면서, 아직 확보하지 못한 표현을 더 담는 후보만 선택한다. 한국어 두 글자 묶음과 대소문자를 통일한 단어를 쓰며 후보 페이지에서 드문 표현에 가중치를 준다. 동점이면 검색 순위를 유지한다. 페이지 전체가 들어가지 않으면 실제로 보낼 청크만 점수화하여, 문맥에서 잘린 뒤쪽 내용으로 점수를 얻지 못하게 한다. `seed_rank`, `replaced_seed_rank`, `selection_reason`으로 선택 이유를 확인할 수 있다. 보수적인 문자열 기반 선택이며 의미상 완전성을 보장하지는 않는다. 청크 모드·인덱스·출처 무결성·페이지 및 글자 한도는 유지하고 새 설정·의존성은 추가하지 않았다.

| 오프라인 검색 지표 | 기존 페이지 선택 | 개선된 페이지 선택 |
| --- | ---: | ---: |
| 문맥에 필수 근거 전체 확보 | 47/48 | 48/48 |
| 개별 근거 그룹 확보 | 74/75 | 75/75 |
| 다중 문서 필수 페이지 전체 확보 | 17/18 | 18/18 |
| 평균 문맥 글자 수 | 4,222.52 | 4,233.82 |
| 최대 문맥 글자 수 | 4,708 | 4,559 |

남아 있던 후보 목록 57건과 기존 문맥 60건이 모두 재현됐다. 두 선택 방식에 같은 후보를 제공했으며 후보에는 이미 답변 가능 48문항의 필수 근거가 모두 있었다. 60문항 중 32개의 문맥이 바뀌었고, 필수 근거 전체 확보 개선은 q51 한 건, 악화는 없었다. q51은 앞선 네 출처를 유지하면서 다섯 번째 페이지를 검색 후보 9위의 `04_contract_settlement.pdf` 3페이지로 교체했다. 문맥은 4,031자에서 3,801자로 줄었다. **이는 알려진 질문의 검색 근거 확보율이며 답변 정확도 100%가 아니다.** 새 답변·AI 채점·사람 검토·독립 평가는 수행하지 않았다.

근거: [비교 결과와 과거 오류 점검](../eval/results/phase6_selection_20261016/comparison.json), [고정한 실행 조건](../eval/results/phase6_selection_20261016/protocol.json), [테스트·검증 기록](../eval/results/phase6_selection_20261016/verification.json). 소스가 바뀌어 원래 복구 계획은 설계대로 현재 코드 확인에서 막힌다. 원본은 보존하고 같은 이전 답변 87건을 대상으로 [새 오프라인 계획](../eval/results/phase6_review_recovery_selection_20261016/plan.json)을 준비해 현재 코드 검사를 통과했다. 이후 해당 채점을 복구해도 이번 선택 방식이 아닌 과거 저장 답변을 평가한다. 충전·채점 보류는 유지하며 어느 복구 계획도 실행하지 않았다.

```powershell
# 설치된 로컬 임베딩 모델로 재현. 기존 결과를 보존하도록 새 폴더 지정.
.\.venv\Scripts\python.exe -X utf8 -m eval.selection compare --source-dir eval/results/phase6_quality_20261016 --output-dir eval/results/selection_new_run
# 저장 비교 결과의 오프라인 감사. 모델 호출 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.selection verify --output-dir eval/results/phase6_selection_20261016
```

이번 개정은 완료한 로컬 변경을 GitHub에 게시하도록 묶었으며 Cloud 실행 검증은 계속 보류한다. 다음 품질 작업은 새 독립 질문 준비이며, 사용자가 API 사용을 재개하면 실제 응답의 진단 기록과 새 선택 방식의 답변 품질을 확인한다. 사용성은 보류하고 동시 접속 검사는 제외한다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-16 | 코드 변경 전에 실행 계획 작성. 사용자가 개발·테스트를 승인했다. 별도 dev-log 스킬 미설치로 이 문서에 변경 이력을 기록한다. |
| 2026-10-16 | 선택형 페이지 문맥 검색과 요구 항목·조건 보존 지시 구현. 개발용 검색으로 pages5 선택, 테스트 267개와 실제 답변·AI 채점 각 6건 완료. 증빙 및 README 2개 연결. 로컬 범위 완료이며 Cloud에는 게시하지 않음. |
| 2026-10-16 | b89ed76 코드 푸시 완료와 pages/5/6000 활성화 우선·Phase 7 사용성 보류 결정을 기록했다. Cloud Settings 적용 절차를 준비했으며 관리 도구 연결이 없어 서버 값·활성화는 미확인이다. 문서만 갱신했으며 별도 dev-log는 미설치로 생략했다. |
| 2026-10-16 | 사용자의 설정 변경·Reboot 완료 보고를 기록하고 목표를 RAG 로직·측정된 정확도·정교한 근거 처리·개선 설명으로 명확히 했다. 동시 접속 검사는 제외하고 사용성 보류를 유지했다. 추적·평가를 다음 제안으로 우선했으며 새 원격 검사는 실행하지 않았다. 별도 dev-log 미설치로 문서 이력에 기록했다. |
| 2026-10-16 | 추적 기록·원격 대조 수정 및 실제 LangSmith 검증, 고정한 답변 120회 비교를 완료했다. 일부 채점 실패와 잔액 부족을 확인하고 87건 복구를 오프라인 준비했다. 사용자 결정으로 충전·채점 보류. 최종 테스트 305개 통과·과거 산출물 90개 보존. 로컬 변경이며 별도 dev-log는 미설치로 생략. |
| 2026-10-16 | 검증 규칙·위치 기록과 마지막 페이지 선택 개선. 오프라인 근거 확보 47/48→48/48, 전체 근거 확보 악화 없음. 테스트 347개 통과·기존 파일 336개 보존·87건 복구 계획만 새로 준비. 모델 호출·푸시·Cloud 변경 없음. 별도 dev-log 미설치로 여기에 기록. |
