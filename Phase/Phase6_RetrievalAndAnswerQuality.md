# Phase 6 — Retrieval and Answer Quality `✅ Agreed portfolio scope complete`

> Improve complete evidence retrieval and condition-preserving answers with a bounded, auditable context.

**Started**: 2026-10-16 (Asia/Seoul)\
**Initial implementation completed**: 2026-10-16; final agreed improvements completed 2026-10-19\
**Status**: ✅ Agreed improvements implemented, tested, and published as [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4). Latest software suite: 488 passed. The owner reports completing the Cloud 4096-token setting. Earlier evaluation failures and uncompleted independent review remain explicit; no required development remains in this portfolio scope.\
**Prerequisites**: Phases 1–4 implemented; Phase 5 demo deployed. The user explicitly deferred remaining Phase 5 checks and authorized Phase 6 documentation, development, and tests.\
**Technology**: Python 3.12, existing E5/Chroma/Claude stack, pytest.

**Latest closeout (2026-10-19):** [Final portfolio improvements](#final-portfolio-improvements--2026-10-19) cover required answer items, all-quotation display, and observed citation gaps. Seven live answers checked the first two changes; the citation follow-up used ten calls across preserved attempts and ended with four accepted cases. No AI judges or automatic retries. The earlier frozen final scores remain content 15/20 and content/citations 13/20; no new overall score is inferred.

**Earlier follow-up (2026-10-19):** [Separate grading and rule selection](#separate-grading-and-complete-rule-selection--2026-10-19) are implemented locally; **483 tests** pass. Offline dev evidence improves **14/16→16/16**, retaining known-v2 **48/48**. Live grading is partial: 10 requests, 6 accepted stages, 3 validation rejections and 1 provider error. No new answers or final questions were evaluated; the earlier complete answer comparison remains 17/20→17/20. The previous snapshot was published as `8686fff`; this follow-up is local.

**Reading the history:** Dated checkpoints below retain their status and next steps at that time. Their references to local-only work or pending publication are historical; the latest status above and final improvements below supersede those plans.

## Earlier user decision — 2026-10-16

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

### Dataset tooling and v3 preparation — 2026-10-19

The owner authorized development and tests for dataset tooling and new questions. The implementation is local; paid evaluation, deployment, and the deferred 87 reviews remain outside this run. Retrieval and answer prompts are unchanged.

| Task | Implementation | Acceptance / verification |
| --- | --- | --- |
| Dataset validation | [datasets.py](../eval/datasets.py): reusable list schema, filename-safe unique IDs, wording duplicates, split/family separation, criteria/evidence completeness, physical page and whitespace-only quote checks | Reject malformed annotations before opening runtime resources; compare normalized wording with v2 |
| Paired evaluator | [quality.py](../eval/quality.py): explicit dataset and dev/final selection, version 2 protocols, calculated call limits, grouped diagnostics and reporting | Freeze/run/audit tested with fake clients; selected questions alone reach generation; references reach only the judge |
| New questions | [questions_v3.json](../eval/questions_v3.json), reproducible from [new_cases.py](../eval/new_cases.py) | 40 questions; 20 dev / 20 final; 16 answerable and 4 unanswerable per split; every quote checked against the PDF |
| Compatibility | Default freeze still uses legacy v2/60 questions and version 1; legacy verification/report text retained | Existing Phase 5/6 artifacts and reports reproduced offline; source PDFs, v1/v2 datasets and old results preserved |

Each split contains four boundary, composite, exception, timing, and unanswerable questions. The full set has 19 multi-document, 13 single-document, and 8 unanswerable cases. New combinations cover installation/transport costs, different budget/legal thresholds, authorization gates, contract changes, emergency procedures, and separate business-day clocks. No normalized question text repeats v2. Families are disjoint between dev and final by annotation; shared rules and semantic similarity still exist. These are AI-authored scenarios on the same small synthetic corpus, not an externally authored blind benchmark. PDF matching checks provenance, not rubric completeness; independent human review remains pending.

For a custom list, required fields are `id`, `split` (`dev`/`final`), `family`, `category` (`single_document`/`multi_document`/`unanswerable`), `question`, `answerable`, `expected_answer`, `grading_criteria`, and `evidence_groups`. Optional `test_type` gives the second report grouping. Each evidence group contains `id`, `claim`, and nonempty `any_of` alternatives with PDF `document`, physical `page` (starting at 1), and `quote`. Unanswerable questions have no evidence groups and require the existing full-abstention contract; partial answers were not introduced.

Run from the project root:

```powershell
# Offline schema, source quotes, split counts and duplicate-wording check.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality validate --dataset eval/questions_v3.json --against eval/questions_v2.json
# Offline reproducibility check of the saved v3 specification.
.\.venv\Scripts\python.exe -X utf8 -m eval.new_cases
# Prepare a NEW directory; requires the existing index and cached local E5 model.
# No questions are searched/generated by freeze. It opens the index to record its configuration.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality freeze --dataset eval/questions_v3.json --split dev --max-calls 80 --output-dir eval/results/v3_dev_new_run
```

One 20-question split × two configurations permits at most 40 answers and 40 AI reviews (80 total requests). `--max-calls` caps the planned requests, not monetary spend; a smaller limit rejects the full plan instead of silently dropping questions. Version 2 freezes the selected questions, the entire source dataset hash, split, code/PDF/prompt/settings hashes and execution limits. Any source-dataset change, including the reserved split, blocks reuse for live execution. Historical auditing uses the frozen snapshot without requiring the current source dataset, credentials, or models.

Only after API evaluation is explicitly resumed, `python -m eval.quality run --output-dir <frozen-directory>` makes live requests; `--resume` reuses completed attempts and never repeats a pending or failed request. `verify` and `report` use the same directory offline. New reports separate RAG errors, failure stages, skipped grading, judge errors, missing grades, confirmed passes, and fully assessed outcomes. Missing grades do not become a measured accuracy. Grouped results are available by category and test type. Existing reports are protected from overwriting.

The final split was validated for annotations only; no v3 retrieval scores, generated answers, AI grades, or human grades were produced. Keep its results unobserved while tuning on dev; once used to guide changes, it becomes a regression set. The next task is explicit live dev evaluation, followed by fixed-implementation final evaluation when authorized. The old 87-review recovery plans remain historical; changes to evaluation code invalidate their current-source guard. Prepare a new recovery plan before any future review-only run; those reviews still assess the old saved answers.

The full suite passed **409 tests in 41.14 seconds** (62 new). All 359 baseline files, including 340 historical evaluation artifacts, remain byte-identical. Freezing the 20-question development selection and checking current conditions against the real local index also passed without question retrieval or generation. Verification is recorded in [the offline development record](../eval/results/phase6_datasets_20261019/verification.json). Separate dev-log is unavailable; history is recorded below.

### V3 development evaluation — 2026-10-19

The owner reported replenished credits and requested the next step. This run measures the latest implementation on the **20 v3 dev questions**, comparing chunks/k=5 with pages/k=5/6,000 characters. It ran locally from 10:03 to 10:08 KST using `claude-sonnet-5-5` for generation and separate AI grading. Code, dataset, PDFs, prompts and settings were frozen before execution; none changed during the run. Final questions and the historical 87-review backlog were not executed.

| Measure | chunks/5 | pages/5 |
| --- | ---: | ---: |
| Original AI passes / all questions, including failed outputs | 14/20 (70%) | 15/20 (75%) |
| Original AI passes / answerable questions | 10/16 | 11/16 |
| Complete required-quote coverage | 10/16 | 12/16 |
| Evidence groups retrieved | 33/43 | 39/43 |
| Validated responses | 20/20 | 19/20 |
| Completed AI reviews / valid responses | 20/20 | 19/19 |
| Abstention on unanswerable questions | 4/4 | 4/4 |
| Abstentions on answerable questions | 2 | 0 |
| Mean / p95 RAG latency, successful responses | 5.05 / 10.70 seconds | 5.37 / 13.06 seconds |
| Generation input / output tokens, including failed outputs | 98,938 / 11,636 | 119,142 / 13,226 |

All eligible responses were graded. The invalid page response counts as an unsuccessful end-to-end outcome, with no judge call; it is not an unresolved grading failure. The frozen limit was 80 model requests; actual use was **40 generation + 39 grading = 79**, with no retries or provider errors. Total grading input/output tokens were 299,831/16,761; caches were unused. Page mode used 20.42% more generation input tokens and 31.55% more context characters. These are usage/latency observations, not a currency estimate or a Cloud performance test.

The original paired grades show gains on `v3_d01`, `v3_d05`, a regression on `v3_d15`, and 19 jointly graded pairs. Only `v3_d05` clearly demonstrates the observed retrieval improvement; the `d01`/`d15` changes involve disputed grading interpretations. The one-question net difference does not establish general answer-quality improvement. Multi-document passes are 5/10 versus 6/10; composite cases remain the weakest group at 1/4 versus 2/4.

| Case | Observation | Follow-up |
| --- | --- | --- |
| `d05` | Chunks lacked the approval table and abstained. Pages selected the table at candidate rank 11 and passed. | Preserve grounded abstention; improve access to required clauses. |
| `d07`, `d08` | Pages omitted the budget rule at candidate rank 8 and the quotation rule at rank 15. Answers missed the review-before-approval timing and the one-quotation/reasonableness requirements respectively. | Improve final context selection using dev cases; references must remain outside generation. |
| `d04` | Pages had every required quote, but `quote_not_in_source` at `/claims/0/evidence/1/quote` blocked the answer. Chunks instead lacked the budget rule and inferred a waiver from an example. | Keep exact contiguous-quote validation. The rejected raw answer was not retained, so its exact text alteration cannot be diagnosed. Investigate general quote instructions and source binding. |
| `d01`, `d11`, `d15` | The judge penalized an equivalent final-approver answer, treated the question's premise inconsistently, or rejected the ordinary business-day interpretation. `d11` also raises support for extra explanatory claims. | Clarify semantic equivalence, premise handling and permitted inference; retain the raw grades for independent adjudication. |
| `d10` | Both modes passed by inferring the 700만원 authority from 550만원/720만원 examples while the explicit authority table was absent. | Review the inference and reference requirements; quote coverage and AI correctness are distinct measurements. |

This analysis is an agent review, **not completed human adjudication**. No corrected accuracy was manufactured and no stored grade was overwritten. The existing 34-entry human queue remains intact; `d01`, `d10`, `d11`, `d15` are additional question-level review candidates recorded in the separate analysis.

Next: clarify the disputed grading policy, develop context-selection and quote-generation improvements against dev, then reevaluate dev. Freeze code and scoring criteria before executing the reserved final 20 questions. Final annotations were already inspected during preparation, but no final retrieval scores, answers or grades have been produced. The shared synthetic corpus, AI authorship, same-model grading and single-run sample limit external conclusions.

Evidence: [protocol](../eval/results/v3_dev_20261019_1003/protocol.json), [answers and original reviews](../eval/results/v3_dev_20261019_1003/answers.json), [report](../eval/results/v3_dev_20261019_1003/report.md), [case analysis](../eval/results/v3_dev_20261019_1003/analysis.json), [verification](../eval/results/v3_dev_20261019_1003/verification.json). Offline `verify` and report reproduction passed. All **376 baseline files**, including **341 prior evaluation files**, remain byte-identical. Code/tests still match the previous **409-test** snapshot; this evaluation turn did not rerun the software suite. No commit, push or Cloud changes were made.

```powershell
# Offline; no model requests or credentials required.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/v3_dev_20261019_1003
.\.venv\Scripts\python.exe -X utf8 -m eval.quality report --output-dir eval/results/v3_dev_20261019_1003
```

### V3 development refinement — 2026-10-19

**Implementation and dev testing completed; overall answer-accuracy improvement not established.** The owner authorized this development and test step. Original datasets, PDFs, answers and grades are preserved, and no final questions were executed.

| Change | Implemented behavior | Verification |
| --- | --- | --- |
| Context selection | `query_and_section_coverage_v2` retains the existing final-slot pass, then can replace redundant non-leading slots. It protects the first two hits when possible, all covered question features, and existing focused section-title features. The last question sentence focuses title matching; a swap must add a requested section. | Dev required quotes 12/16→14/16 (`d07`, `d08`); known v2 48/48 retained. No complete-evidence regressions in either replay. No extra search, references, dependencies, or clipping. |
| Generation instructions | Require original contiguous table text or separate evidence entries; verify source binding. Reject deriving a new general rule from isolated examples or silence. The common instructions apply to both retrieval modes. | All 20 new outputs validated; table-row concatenation is rejected in regression tests. Strict validation and one generation attempt remain. |
| Judge instructions | Clarify equivalent meanings, question facts versus policy claims, logical evidence combination, ordinary word meanings and forbidden example-based extrapolation. | The old `d15` answer now passes, but real grading still violates parts of the instructions. Prompt clarification is not a complete grading fix. |
| Comparable evaluation | New [refinement.py](../eval/refinement.py) freezes an explicit dev baseline, reuses its 20 page answers, generates only 20 new answers, and grades both with the same revised judge. | Frozen code/data/settings and request limits; durable attempts; no automatic retries; reject pending requests, source drift, changed links and report overwrites. Offline audit and report reproduction passed. |

The initial broader lexical replacement experiment regressed on dev and was rejected before live calls. The accepted selector requires added direct section coverage and preserves existing coverage; it remains a heuristic, not a guarantee of semantic completeness. Runtime defaults, the five-source/6,000-character candidate setting, source text and index contents are unchanged.

| Comparable page-mode measure | Saved answers, regraded | Refined answers |
| --- | ---: | ---: |
| End-to-end AI passes | 17/20 (85%) | 17/20 (85%) |
| Complete required-quote coverage | 12/16 | 14/16 |
| Evidence groups | 39/43 | 41/43 |
| Validated outputs | 19/20 | 20/20 |
| Valid responses graded | 19/19 | 20/20 |
| Unanswerable cases correctly abstained | 4/4 | 4/4 |
| Answerable cases abstained | 0 | 1 (`d10`) |
| Successful-response mean latency | 5.37 s (earlier run) | 4.21 s |

The original baseline's **15/20** was produced by the previous judge instructions; regrading those same answers changes `d07` and `d15` to passes, yielding **17/20**. Do not claim 15→17 as an implementation gain. Under the same revised judge, gains `d04`/`d08` and regressions `d10`/`d12` cancel. Retrieval selection and generation instructions changed together; their separate contributions and latency differences are not isolated.

Remaining evidence:

- `d07`: the new answer includes the budget rule and explicitly states review before approval. The judge nevertheless passed the old answer by referring to unseen `R3` and extrapolating from an example. Reference contamination remains a grading concern.
- `d10`: the explicit approval table is still missing. The new answer abstains rather than interpolating between examples; this is an end-to-end failure. The judge still passed the old interpolation despite its new instructions.
- `d11`: the approval table is absent, and the rubric demands restating the question's team-approval premise. The new answer gives the requested advance-payment rejection and finance review, but still fails that criterion. Retrieval and rubric interpretation need separate review.
- `d12`: both correctness criteria pass, but the judge rejects a combination it calls logically valid because no single source sentence says everything. The first new claim also lacks a direct `S2` citation for its budget assertion. Review grading consistency and per-claim source completeness; do not silently correct the score.
- `d04`: the new quote passed, but a single run does not prove the failure is eliminated; the old rejected raw text remains unavailable.

Actual requests were **20 new answers + 39 new reviews = 59**, with no provider/review errors or retries. New generation used 124,273 input / 9,811 output tokens; grading used 348,356 / 15,000. The 20 baseline answers were reused without generation. The software suite passed **439 tests in 46.05 seconds** (30 new); saved live contexts exactly match all 20 offline dev replays. All **434 protected files**, including **427 historical evaluation artifacts**, remain byte-identical. Human review is still pending; no commit, push or Cloud change was performed.

Next: design grounding review so reference answers cannot supply missing retrieved evidence; calibrate it with independent adjudication. Address the remaining explicit-rule retrieval and per-claim citation gaps, reevaluate dev, then freeze code/scoring before final evaluation. The final 20 questions remain reserved. Historical 87-review recovery now also needs compatibility with the original judge prompt; a newly generated recovery plan alone is not enough. Historical selector-replay commands have a deliberate current-source guard; their old records are preserved, while current replay evidence is linked below.

Evidence: [offline retrieval replay](../eval/results/v3_refinement_checks_20261019/retrieval_replay.json), [software tests](../eval/results/v3_refinement_checks_20261019/software_tests.json), [live report](../eval/results/v3_refinement_dev_20261019/report.md), [case analysis](../eval/results/v3_refinement_dev_20261019/analysis.json), [verification](../eval/results/v3_refinement_dev_20261019/verification.json).

```powershell
# Offline preparation into a NEW folder; the baseline must be an explicit dev split.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement freeze --source-dir eval/results/v3_dev_20261019_1003 --output-dir eval/results/v3_refinement_new_run --max-calls 59
# Billable, at most 59 model calls for this baseline; not needed to verify saved results.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement run --output-dir eval/results/v3_refinement_new_run
# Offline verification/reproduction of the completed run.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement verify --output-dir eval/results/v3_refinement_dev_20261019
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement report --output-dir eval/results/v3_refinement_dev_20261019
```

### Separate grading and complete rule selection — 2026-10-19

The owner approved publishing the reviewed snapshot and developing priorities 1 and 2. Commit `8686fff76349cd1a2b615a5b365c80471941d390` was pushed to `origin/main`; local, upstream and GitHub tips matched. The new work below starts after that publication and is not part of that commit.

| Task | Planned behavior | Completion checks |
| --- | --- | --- |
| Separate grading | Add a frozen saved-answer evaluator with independent correctness and grounding requests. Grounding receives only the question, answer/claims and retrieved sources; expected answers, reference passages and correctness judgments never enter that request. Keep original combined-judge artifacts reproducible. | Payload-isolation tests, source/claim binding checks, ambiguous/error grades reported separately, durable stage attempts and bounded calls. Review disputed dev cases without silently changing old grades. |
| Complete rule selection | Recover relevant rule sections already present in the candidate list, including approval authority, without reference annotations or extra model/search calls. | Replay all 20 dev and 60 known-v2 questions; retain existing complete evidence, source limits and exact text. Add general selection regression tests. |
| Verification | Run meaningful unit/regression tests and a small frozen live check of split grading after software checks. | Preserve all historical artifacts and final questions. Record observations separately from human adjudication and overall answer accuracy. |

Status: both implementations and software/retrieval tests are complete. Live judge calibration remains partial; no independent human adjudication or new answer-accuracy measurement was completed.

- [split_judge.py](../eval/split_judge.py) builds allowlisted, independent correctness and grounding inputs. References and expected answers cannot enter grounding. Correctness never receives grounding decisions. Grounding also reports claim-level citation completeness separately. Every claim/criterion is a required API response field; directly cited evidence is selected by an index restricted to that claim's existing citations. Retrieved evidence still requires exact original quotes.
- [review_split.py](../eval/review_split.py) freezes selected saved dev answers, code, prompts, settings and request limits. Each stage has its own durable attempt and audited input/schema/result links. Errors remain unassessed; pending calls and completed/failed calls are not automatically repeated. Earlier frozen schemas and combined-judge reports remain auditable.
- `query_and_section_topics_v3` normalizes business-rule terms, including approver/approval authority wording. It preserves leading hits, existing question-text coverage and existing requested rule topics; gaining an explicit topic can replace incidental Korean character-pair title matches. Requested topics use the final request sentence, while an approval-role assertion in the scenario still requires evidence. No question IDs, document filenames, amounts or reference annotations drive selection. A broader topic experiment displaced a quotation clause and was rejected; the final replay has no complete-evidence regressions.

| Verification | Observed result |
| --- | --- |
| Full software suite | **483 passed in 22.25 s**, 44 new tests since 439 |
| Dev retrieval replay | **14/16→16/16**, gains `d10`/`d11`, no regressions |
| Known-v2 retrieval replay | **48/48→48/48**, no regressions |
| Historical preservation | **522 files**, including **515 prior evaluation artifacts**, byte-identical |
| Live diagnostic reviews | **10 requests**, 6 accepted stages, 3 validation rejections, 1 provider error; no automatic retry |
| New answers / final questions | **0 / 0** |

The first three diagnostic runs exposed mixed support/citation proof, omitted claim decisions, and a quote outside a particular claim's citations. All rejected responses were retained; the fixes separated proof fields, required each item in the response schema, and constrained citation selection to existing citation indices. The final run accepted four stages for two saved `before` answers, then stopped on `ClaudeError` while starting the `after` reviews. Its provider response was not retained, so the specific API cause is unknown; credit shortage is not established. The intended before/after grading comparison did **not** complete. Observed usage across runs was 59,734 input and 12,467 output tokens; usage for the provider error is unavailable.

Input separation is verified, but AI semantic consistency is not solved. In the latest `d07` review, the model marks support true while acknowledging an example-based generalization; it marks citation completeness false. `d12` also passes correctness/support but fails citation completeness. These are unadjusted AI decisions on old answers, not human findings or evidence that new RAG answers improved. Next: independently adjudicate the grading disputes, investigate the provider error before more paid review, improve generated claim citations, then generate/review dev answers with the new selector. Freeze code/scoring before the reserved final 20.

Evidence: [retrieval replay](../eval/results/v3_split_checks_20261019/retrieval_replay.json), [final tests](../eval/results/v3_split_checks_20261019/software_tests_indices.json), [verification](../eval/results/v3_split_checks_20261019/verification.json), [partial live report](../eval/results/v3_split_review_indices_20261019/report.md), [case analysis](../eval/results/v3_split_review_indices_20261019/analysis.json). Earlier failed attempts are retained in `v3_split_review_20261019`, `v3_split_review_fixed_20261019` and `v3_split_review_keyed_20261019`.

```powershell
# Offline: audit attempts and reproduce the partial report; no model calls.
.\.venv\Scripts\python.exe -X utf8 -m eval.review_split report --output-dir eval/results/v3_split_review_indices_20261019
```

`verify` requires a completed run and deliberately does not declare this partial run complete. New paid execution requires a new frozen plan; the stopped output is retained. Separate dev-log is unavailable; the Phase change log records this work.

### Bounded final closeout — 2026-10-19

The owner limited the remaining work to disputed development cases, one final evaluation and a demonstration check. Further judge development and historical review recovery are deferred. The fixed scoring policy accepts rule application but not generalization from examples, distinguishes required answers from restated premises, and checks each claim's attached citations. Codex reviewed the original PDFs; this is **agent review, not independent human adjudication**.

`llm.py` now exposes allowlisted error categories and numeric HTTP status without provider bodies; `rag.py` and saved answer records retain the diagnostic. The prior provider error remains unexplained because its response was not recorded. This run had no provider errors. Retrieval and generation instructions were unchanged. The existing error tests were strengthened and one record-propagation test added: **484 tests passed in 18.33 seconds**.

| Measure | Observed result |
| --- | --- |
| Six disputed/control dev cases | 5/6 meet requirements; d12 inserted table separators into quotes and was blocked |
| Final execution | 20/20 validated responses; 20 generation calls; no AI judge calls |
| Final complete evidence retrieval | 12/16 answerable cases |
| Final content requirements | 15/20 overall; 11/16 answerable |
| Final content plus complete claim citations | 13/20 |
| Unanswerable questions | 4/4 appropriately abstained |
| Latency, excluding initialization | Mean 5.193 s; median 4.341 s; maximum 11.198 s |
| Total new model requests | 26 answers, 0 judges, 0 automatic retries; two non-generation Models API checks |
| Tokens across all 26 answers | 163,233 input / 17,920 output; no monetary estimate |
| Demo | Saved-answer AppTest: 3 answers, 1 abstention, 1 blocked output; local HTTP startup and restart passed |
| Historical preservation | 554 files unchanged; code/scoring identical across dev and final |

Final failures are retained: f01/f07/f09 lack required retrieved rules and abstain; f04 misses the contract-amendment rule and omits the amended contract; f08 omits account-verification documents from the answer text despite retrieving/citing them; f03/f05 omit a threshold or timing clause from claim citations. No tuning or rerunning occurred within that frozen final execution. Later fixes used observed cases as regressions, as documented below; the original scores remain unchanged. These same-corpus questions are now known regression cases; the scores are not proof of general performance or directly comparable to earlier automated-judge scores.

See the [report and all 20 human-review items](../eval/results/v3_closeout_20261019/report.md), [summary](../eval/results/v3_closeout_20261019/summary.json), [verification](../eval/results/v3_closeout_20261019/verification.json), [test output](../eval/results/v3_closeout_20261019/pytest.txt) and [demo check](../eval/results/v3_closeout_20261019/demo_check.json). The one-off `run.py` preserves attempts and refuses existing output folders; it is an archived execution, not a command to rerun this final set. UI results replay saved live answers; HTTP readiness excludes model warmup and does not verify the remote Cloud app. Independent human review is pending, especially interpretation of f03/f05/f08. This bounded execution and its documentation were completed with those limits. It was subsequently published, and the separately authorized focused improvements below followed; this archived 20-question run was not repeated. Independent grading is deferred, not a remaining portfolio completion gate. Separate dev-log is unavailable; history is recorded below.

### Final portfolio improvements — 2026-10-19

The owner approved improvements 1, 2, and 4 after checking five demo answers. Additional complex retrieval work (item 3) remains optional. The completed changes are:

| Change | Behavior and evidence |
| --- | --- |
| 1. Required answer items | Generic instructions require basic and conditional documents explicitly in the answer. Seven live answers included six answerable cases and one correct abstention; all three bank-related answers named account-verification documents. [Review](../eval/results/completeness_display_20261019/review.json) |
| 2. All supporting quotations | Each source shows all distinct claim quotations in order, preserves separate passages, and supports old saved answers. Four meaningful display tests added. The first AppTest replay checked seven answers / 11 source expanders / 23 quotations. [Replay](../eval/results/completeness_display_20261019/display_check.json) |
| 4. Complete claim citations | Instructions retain each claim’s actors, thresholds, timing, exceptions and estimate qualifiers, including complete sentences and relevant table conditions. Final checks covered threshold, timing, explicit PO responsibility and abstention: four accepted cases, 11 claims, 16 claim quotations. [Review](../eval/results/citation_completeness_20261019/review.json) |

The citation follow-up made **10 answer calls, zero judge calls, and zero automatic retries**. Its first two calls included a successful threshold answer and an incomplete response at the old 2,048-token cap; the other two planned cases were not executed in that round. Four explicit checks at 4,096 tokens produced valid responses but retained a timing-quotation/qualifier issue. After whole-sentence and qualifier instructions, the final four cases passed Codex source review. All attempts and earlier failures are retained. The first two improvements used a separate seven answer calls; neither result is an independent holdout or a new overall accuracy estimate.

The output default is now **4,096 tokens**, with one retrieval, at most one generation call, a 30-second timeout, and no automatic retry unchanged. Existing explicit settings take precedence. The latest [software record](../eval/results/citation_completeness_20261019/software_tests.json) and [test log](../eval/results/citation_completeness_20261019/final/pytest.txt) report **488 passed in 72.75 seconds**. The final [Streamlit replay](../eval/results/citation_completeness_20261019/display_check.json) verified four saved answers, nine source expanders and 16 quotations without model calls. [Verification](../eval/results/citation_completeness_20261019/verification.json) preserves all 621 preexisting files from the citation-follow-up snapshot. Historical artifacts retain their execution-time publication/settings fields.

The implementation was published as [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4). The owner now reports completing the Cloud `ANTHROPIC_MAX_TOKENS=4096` change; earlier pages/5/6000 and reboot were also owner-reported. No fresh latest-release Cloud question run, restart, or effective-setting inspection was independently observed. The owner’s earlier five-answer check is separate from the local final regression.

The agreed portfolio scope is complete. Exact-source validation is unchanged; semantic completeness remains a generation instruction checked by Codex, not a universal automatic guarantee. Broad monitor-receipt retrieval still lacks settlement timing, other recorded retrieval failures remain, and independent human grading, the old 87 reviews/34-item queue, Phase 7, and production operations are deferred. The original 20-question scores are unchanged. No additional development or paid evaluation is required to close this scope.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-16 | Created the implementation plan before code changes. User authorized development and tests. Separate dev-log skill unavailable; history is maintained here. |
| 2026-10-16 | Implemented opt-in bounded page retrieval and item/condition-preserving answer instructions; selected pages5 on development retrieval, completed 267 tests and six live/AI-reviewed cases, linked evidence and both READMEs. Local scope complete; no Cloud publishing. |
| 2026-10-16 | Recorded successful code publication as b89ed76 and the user's decision to activate pages/5/6000 first while deferring Phase 7 usability. Prepared Cloud Settings instructions; server values and activation are unverified because no connected Cloud administration tool is available. Documentation only; separate dev-log unavailable. |
| 2026-10-16 | Recorded the owner's settings/reboot completion report and clarified the RAG demonstration objective: logic, measured accuracy, precise evidence, and explained improvements. Excluded concurrency testing; kept usability deferred. Prioritized tracing/evaluation proposals without executing new remote checks. Separate dev-log unavailable; history recorded here. |
| 2026-10-16 | Completed trace metadata/readback fixes, verified real LangSmith, ran the frozen 120-answer comparison, diagnosed partial grading and insufficient credit, and prepared 87 review recoveries offline. Owner deferred charging/grading. Final 305 tests passed; historical 90 artifacts preserved. Local changes only; separate dev-log unavailable. |
| 2026-10-16 | Added safe validation-rule/path records and conservative final-page selection; offline coverage improved 47/48 to 48/48 with no complete-evidence regressions. 347 tests passed, 336 artifacts preserved, and an updated 87-review plan prepared without execution. No model calls, push, or Cloud change; dev-log unavailable. |
| 2026-10-19 | Implemented reusable dataset validation, split-specific version 2 evaluation protocols, call planning and grouped reports; added 40 PDF-checked v3 questions. Tested locally and retained legacy artifacts. No paid evaluation or publication; dev-log unavailable. |
| 2026-10-19 | After the owner funded credits, completed v3 dev comparison with 79 model calls; original AI passes 14/20 and 15/20, one quote-validation failure, no provider/judge errors. Preserved raw grades and all baseline files; recorded retrieval failures and grading disputes. Final questions, old review recovery and Cloud unchanged; dev-log unavailable. |
| 2026-10-19 | Implemented section-aware context refinement, quotation/inference guidance, revised judge instructions and a saved-answer comparison tool. 439 tests passed; 59 live calls. Coverage 12/16→14/16 and valid outputs 19/20→20/20, but same-judge passes 17/20→17/20. Preserved 434 files and documented remaining grading/retrieval issues. Final evaluation and publication pending; dev-log unavailable. |
| 2026-10-19 | Published 192 reviewed files as 8686fff, then implemented separate grading and rule-topic selection locally. 483 tests; dev evidence 14/16→16/16, known-v2 48/48 retained. Live review partial: 10 requests, 6 accepted stages, 3 validation rejections, 1 provider error. Preserved 522 files; new answers/final evaluation and independent adjudication pending. Dev-log unavailable; recorded here. |
| 2026-10-19 | Bounded closeout: safe provider diagnostics, 484 tests, 6 dev + 20 final answers and no judges. Final content 15/20, content/citations 13/20 by Codex; 554 original files preserved. Demo replay/restart passed; human review and publication pending. Further evaluator work deferred; dev-log unavailable. |
| 2026-10-19 | Recorded completed improvements 1/2/4, 488 tests, seven required-item checks and ten citation-follow-up calls ending in four accepted cases; preserved failures and old scores. Linked publication 175bda7 and owner-reported 4096-token setting; closed the agreed scope. Documentation only this turn; dev-log unavailable. |

---

# Phase 6 — 검색·답변 품질 개선 `✅ 합의한 포트폴리오 범위 완료`

> 길이를 제한하고 근거를 추적할 수 있는 문맥으로 필수 근거 검색과 조건을 보존하는 답변을 개선한다.

**시작일**: 2026-10-16 (한국 시간)\
**최초 구현 완료일**: 2026-10-16; 합의한 최종 개선 완료일 2026-10-19\
**상태**: ✅ 합의한 개선을 구현·테스트하고 [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4)으로 게시했다. 최신 소프트웨어 테스트 488개 통과. 사용자가 Cloud 4096토큰 설정 완료를 보고했다. 과거 평가 실패·독립 검토 미완료는 명시하며 이 포트폴리오 범위의 필수 잔여 개발은 없다.\
**선행 조건**: Phase 1~4 구현, Phase 5 데모 배포. 사용자가 남은 Phase 5 검증을 보류하고 Phase 6 문서·개발·테스트를 명시적으로 요청했다.\
**기술 구성**: Python 3.12, 기존 E5/Chroma/Claude, pytest.

**최신 마무리(2026-10-19):** [최종 포트폴리오 개선](#최종-포트폴리오-개선--2026-10-19)은 답변 필수 항목·모든 인용 표시·관측한 인용 누락 보완이다. 앞의 두 개선은 실제 답변 7개, 인용 후속은 실패를 보존한 전체 10회 호출 뒤 최종 4사례 통과를 기록했다. 별도 AI 채점·자동 재시도는 없다. 이전 고정 최종 점수는 내용 15/20·인용까지 13/20으로 보존하며 새 전체 성능 점수를 추정하지 않는다.

**이전 후속(2026-10-19):** [채점 분리·규정 선택](#채점-분리와-규정-선택-보완--2026-10-19)을 로컬 구현했고 **테스트 483개**가 통과했다. 오프라인 개발용 근거는 **14/16→16/16**, 알려진 v2는 **48/48**을 유지했다. 실제 채점은 부분 완료로, 요청 10회 중 6개 단계를 채택하고 3개는 검증에서 거부했으며 1개는 제공업체 오류다. 새 답변·최종 문항은 평가하지 않았고 이전 전체 답변 비교는 17/20→17/20으로 유지한다. 이전 변경은 `8686fff`로 게시했으며 이번 후속은 로컬 상태다.

**이력 읽기:** 아래 날짜별 기록의 상태와 다음 단계는 당시 기준이다. 로컬 변경·게시 대기라는 과거 표현은 현재 잔여 작업을 뜻하지 않으며 위 최신 상태와 아래 최종 개선 기록이 이전 계획을 대체한다.

## 이전 사용자 결정 — 2026-10-16

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

### 평가 도구 확장과 v3 준비 — 2026-10-19

사용자가 평가 도구 확장과 새 질문 작성·테스트를 승인했다. 로컬 구현 범위이며 유료 평가, 배포, 보류 중인 87건 채점은 실행하지 않았다. 검색 로직과 답변 프롬프트는 유지한다.

| 작업 | 구현 | 완료 기준 / 검증 |
| --- | --- | --- |
| 평가셋 검사 | [datasets.py](../eval/datasets.py): 공통 목록 스키마, 파일명으로 안전한 고유 ID, 문구 중복, split/family 분리, 기준·근거 필수값, 실제 페이지·공백 차이만 허용하는 인용 검사 | 잘못된 주석은 실행 자원을 열기 전에 거절하며 기존 v2와 정규화 문구 중복 확인 |
| 비교 평가기 | [quality.py](../eval/quality.py): 데이터셋·dev/final 명시 선택, 버전 2 프로토콜, 호출 한도 계산, 유형별 진단·보고서 | 대역 클라이언트로 고정→실행→감사 검증. 선택 문항만 생성기에 전달하고 정답·참고 근거는 채점기에만 전달 |
| 새 질문 | [questions_v3.json](../eval/questions_v3.json), [new_cases.py](../eval/new_cases.py)에서 재현 | 총 40문항, 개발 20·최종 20. 각 묶음은 답변 가능 16·불가 4이며 모든 인용문을 PDF와 대조 |
| 과거 호환 | 옵션 없는 freeze는 기존 v2 60문항·버전 1을 유지하고 기존 검증·보고서 문구도 유지 | Phase 5/6 저장 산출물과 보고서 오프라인 재현. PDF·v1/v2 평가셋·기존 결과 보존 |

각 묶음에 경계값·복합 조건·예외·기한·답변 불가 질문을 4개씩 포함한다. 전체는 다중 문서 19·단일 문서 13·답변 불가 8개다. 설치·운송비 합산, 예산·법무의 다른 경계값, 승인 단계, 계약 변경, 긴급 절차, 서로 다른 영업일 기산점 등을 조합했다. v2와 정규화한 질문 문구 중복은 없다. family 주석은 dev/final 사이에 겹치지 않지만 공통 규정과 의미 유사성은 남는다. 같은 소규모 합성 문서에 대해 AI가 작성한 시나리오이며 외부 작성자의 블라인드 평가가 아니다. 인용문 일치는 출처를 검증할 뿐 채점 기준의 완전성을 보장하지 않으며 독립적인 사람 검토는 미완료다.

새 목록의 필수 필드는 `id`, `split`(`dev`/`final`), `family`, `category`(`single_document`/`multi_document`/`unanswerable`), `question`, `answerable`, `expected_answer`, `grading_criteria`, `evidence_groups`다. 선택 필드 `test_type`으로 추가 유형별 집계를 한다. 근거 그룹은 `id`, `claim`, 비어 있지 않은 `any_of`를 가지며 각 대안은 PDF 파일명 `document`, 1부터 시작하는 실제 `page`, `quote`를 포함한다. 답변 불가 문항은 근거 그룹이 비어 있고 기존 전체 답변 보류 계약을 따른다. 부분 답변 정책은 추가하지 않았다.

프로젝트 루트에서 실행한다.

```powershell
# 스키마·원문 근거·묶음별 개수·문구 중복 검사. API 호출 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality validate --dataset eval/questions_v3.json --against eval/questions_v2.json
# 저장한 v3가 작성 명세와 같은지 오프라인 검사.
.\.venv\Scripts\python.exe -X utf8 -m eval.new_cases
# 기존 인덱스·로컬 E5 캐시 필요. 매번 새 출력 폴더 지정.
# freeze는 질문 검색·답변 생성 없이 인덱스를 열어 설정을 기록한다.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality freeze --dataset eval/questions_v3.json --split dev --max-calls 80 --output-dir eval/results/v3_dev_new_run
```

20문항 한 묶음을 두 설정으로 비교하면 답변 최대 40회·AI 채점 최대 40회, 합계 최대 80회다. `--max-calls`는 금액이 아닌 계획 요청 수의 상한이다. 한도가 작으면 문항을 몰래 줄이지 않고 전체 계획을 거절한다. 버전 2는 선택 문항, 전체 원본 데이터셋 해시, split, 코드·PDF·프롬프트·설정 해시와 실행 한도를 고정한다. 최종 평가용 묶음을 포함해 원본 데이터셋이 바뀌면 실시간 실행 재사용을 막는다. 과거 결과 감사는 고정 스냅샷을 사용하므로 현재 원본 데이터셋 파일·인증 정보·모델이 필요 없다.

API 평가를 명시적으로 재개한 뒤에만 `python -m eval.quality run --output-dir <고정한-폴더>`로 실제 요청한다. `--resume`은 완료 시도를 재사용하며 pending·실패 요청을 반복하지 않는다. `verify`와 `report`는 같은 폴더를 오프라인으로 검사한다. 새 보고서는 RAG 오류·발생 단계, 채점 건너뛰기, 채점 오류·누락, 확인된 통과, 전체 판정 완료를 구분한다. 미채점을 포함한 수치를 측정한 정확도로 확정하지 않는다. category와 test_type별 결과를 제공하고 기존 보고서를 덮어쓰지 않는다.

최종 평가용 문항은 주석만 검사했다. v3 검색 성능·생성 답변·AI 채점·사람 채점 결과는 만들지 않았다. 개발용으로 조정하는 동안 최종 묶음의 성적은 확인하지 않고, 결과를 변경에 활용한 뒤부터는 회귀 평가셋으로 취급한다. 다음 작업은 승인 후 실제 개발용 평가, 구현을 고정한 뒤 최종 평가다. 기존 87건 복구 계획은 과거 증빙으로 유지하며 평가 코드가 바뀌어 현재 소스 검사에서 차단된다. 향후 채점만 복구하기 전 새 계획을 준비해야 하고, 복구 대상은 여전히 과거 저장 답변이다.

전체 테스트 **409개가 41.14초에 통과**했다(신규 62개). 기존 평가 산출물 340개를 포함한 기준 파일 359개가 바이트 단위로 유지됐다. 실제 로컬 인덱스를 사용한 개발용 20문항 조건 고정·현재 조건 대조도 통과했으며 질문 검색·생성 호출은 없었다. 검증 결과는 [오프라인 개발 기록](../eval/results/phase6_datasets_20261019/verification.json)에 저장했다. 별도 dev-log는 미설치로 아래 변경 이력에 기록한다.

### V3 개발용 평가 — 2026-10-19

사용자가 크레딧 충전과 다음 단계 진행을 요청했다. 최신 구현을 **v3 개발용 20문항**으로 측정하며 chunks/k=5와 pages/k=5/6,000자를 비교했다. 한국 시간 10:03~10:08에 로컬에서 실행했고 `claude-sonnet-5-5`로 답변과 별도 AI 채점을 수행했다. 코드·평가셋·PDF·프롬프트·설정을 실행 전에 고정했으며 실행 중 변경하지 않았다. 최종 문항과 과거 미완료 채점 87건은 실행하지 않았다.

| 지표 | chunks/5 | pages/5 |
| --- | ---: | ---: |
| 원본 AI 통과 / 전체 문항, 출력 실패 포함 | 14/20 (70%) | 15/20 (75%) |
| 원본 AI 통과 / 답변 가능 문항 | 10/16 | 11/16 |
| 필수 인용 근거 전체 확보 | 10/16 | 12/16 |
| 근거 그룹 확보 | 33/43 | 39/43 |
| 출력 검증 통과 응답 | 20/20 | 19/20 |
| AI 채점 완료 / 유효 응답 | 20/20 | 19/19 |
| 답변 불가 문항에서 보류 | 4/4 | 4/4 |
| 답변 가능 문항에서 보류 | 2 | 0 |
| 성공 응답의 평균 / p95 RAG 지연시간 | 5.05 / 10.70초 | 5.37 / 13.06초 |
| 생성 입력 / 출력 토큰, 실패 응답 포함 | 98,938 / 11,636 | 119,142 / 13,226 |

채점 가능한 응답은 모두 채점했다. 무효 페이지 응답은 전체 실행의 실패 결과에 포함하며 채점 요청을 하지 않았고, 미해결 채점 실패와는 구분한다. 한도는 모델 요청 80회였으며 실제 **답변 40회 + 채점 39회 = 79회**를 실행했다. 자동 재시도와 제공업체 오류는 없었다. 채점 입력/출력 토큰 합계는 299,831/16,761이며 캐시는 사용하지 않았다. 페이지 방식의 생성 입력 토큰은 20.42%, 문맥 글자 수는 31.55% 많았다. 금액 추정이나 Cloud 성능 검사가 아닌 이번 실행의 사용량·지연시간 관측이다.

원본 쌍별 판정은 `v3_d01`·`v3_d05` 개선, `v3_d15` 악화이며 두 방식 모두 채점한 문항은 19개다. `v3_d05`에서는 검색 개선이 확인되지만 `d01`·`d15`의 변화에는 채점 해석 논쟁이 있다. 순증 1문항을 일반적인 답변 품질 개선으로 단정하지 않는다. 복수 문서 통과는 5/10·6/10이고, 복합 조건 유형은 1/4·2/4로 가장 약하다.

| 사례 | 관측 | 후속 작업 |
| --- | --- | --- |
| `d05` | 청크는 결재 금액표가 없어 보류했지만 페이지는 후보 11위 금액표를 선택해 통과했다. | 근거 부족 시 보류를 유지하고 필요한 조항 확보를 개선한다. |
| `d07`, `d08` | 페이지도 후보 8위 예산 규정과 15위 견적 규정을 빠뜨려 각각 결재 전 검토 시점, 견적 1부·금액 합리성 검토 조건을 누락했다. | 개발용으로 최종 문맥 선택을 개선하며 정답 주석을 생성에 전달하지 않는다. |
| `d04` | 페이지는 근거를 모두 확보했지만 `/claims/0/evidence/1/quote`에서 `quote_not_in_source`가 발생했다. 청크는 예산 규정 없이 사례로 면제를 추론했다. | 연속 인용 일치 검증을 유지한다. 거부된 답변 원문은 저장하지 않아 정확한 변형 문자는 알 수 없다. 일반적인 인용 지시와 출처 연결을 점검한다. |
| `d01`, `d11`, `d15` | 의미상 동등한 최종 승인자 답변 감점, 질문 전제의 일관되지 않은 취급, 영업일의 통상 해석을 미지원 주장으로 보는 판정이 있다. `d11`은 추가 설명의 근거성도 쟁점이다. | 의미 동등성·전제·허용 추론의 기준을 정리하고 원본 판정을 유지해 독립 검토한다. |
| `d10` | 두 방식 모두 명시적 금액표 없이 550만원·720만원 예시에서 700만원 결재권자를 추론해 통과했다. | 추론과 근거 요구를 검토한다. 인용문 확보율과 AI 정답률은 다른 지표다. |

이 분석은 에이전트 검토이며 **사람 판정 완료가 아니다.** 보정 정답률을 만들거나 저장 점수를 덮어쓰지 않았다. 기존 사람 검토 목록 34건을 유지했고 `d01`·`d10`·`d11`·`d15`는 별도 분석에 추가 문항별 검토 후보로 기록했다.

다음은 채점 해석 정리, 개발용 문항을 이용한 근거 선택·인용 생성 개선, 개발용 재평가다. 이후 코드와 채점 기준을 고정한 뒤 예약한 최종 20문항을 실행한다. 최종 문항 주석은 준비 과정에서 확인했지만 검색 성적·답변·채점은 생성하지 않았다. 같은 합성 문서, AI 작성 질문, 동일 모델 채점과 단일 소표본의 한계를 유지한다.

근거: [프로토콜](../eval/results/v3_dev_20261019_1003/protocol.json), [답변·원본 채점](../eval/results/v3_dev_20261019_1003/answers.json), [보고서](../eval/results/v3_dev_20261019_1003/report.md), [사례 분석](../eval/results/v3_dev_20261019_1003/analysis.json), [검증 기록](../eval/results/v3_dev_20261019_1003/verification.json). 오프라인 `verify`와 보고서 재현을 통과했고 **기준 파일 376개**, 그중 **기존 평가 파일 341개**를 바이트 단위로 보존했다. 코드·테스트는 이전 **409개 테스트 통과** 시점과 같으며 이번 평가에서는 소프트웨어 테스트를 반복하지 않았다. 커밋·푸시·Cloud 변경은 하지 않았다.

```powershell
# 오프라인 검사. 모델 요청·인증 정보 불필요.
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/v3_dev_20261019_1003
.\.venv\Scripts\python.exe -X utf8 -m eval.quality report --output-dir eval/results/v3_dev_20261019_1003
```

### V3 개발 후속 개선 — 2026-10-19

**구현·개발용 테스트 완료, 전체 답변 정확도 개선은 미입증.** 사용자가 이번 개발·테스트를 승인했다. 원본 평가셋·PDF·답변·채점은 보존했고 최종 문항을 실행하지 않았다.

| 변경 | 구현한 동작 | 검증 |
| --- | --- | --- |
| 문맥 선택 | `query_and_section_coverage_v2`는 기존 마지막 슬롯 개선 후 중복된 후순위 슬롯도 바꾼다. 가능한 경우 첫 두 검색 결과, 이미 확보한 질문 표현과 요청한 절 제목 표현을 보존한다. 질문의 마지막 문장으로 절 제목 검색의 초점을 정하고 필요한 절이 추가될 때 교체한다. | 개발용 필수 근거 12/16→14/16(`d07`, `d08`), 알려진 v2 48/48 유지. 두 재생에서 전체 근거 확보 악화 없음. 추가 검색·정답 전달·의존성·본문 자르기 없음. |
| 생성 지시 | 표도 원문 연속 구간을 복사하거나 근거 항목을 나누고 출처 연결을 확인한다. 개별 사례나 문구 부재로 일반 규정을 만들지 않는다. 두 검색 모드의 공통 지시다. | 새 출력 20건 검증 통과. 표 행을 합친 잘못된 인용은 회귀 테스트에서 차단. 엄격한 검증·생성 1회 유지. |
| 채점 지시 | 동등 의미, 질문 상황과 규정 주장, 근거의 논리적 결합, 단어의 통상 의미, 사례 일반화 금지를 명확히 했다. | 이전 `d15` 답변은 통과했지만 실제 채점에서 일부 지시 위반이 남았다. 프롬프트 명확화만으로 채점 문제를 해결한 것은 아니다. |
| 전후 비교 | 새 [refinement.py](../eval/refinement.py)는 개발용 기준 실행을 고정하고 이전 페이지 답변 20개를 재사용한다. 새 답변 20개만 생성하며 양쪽을 같은 새 기준으로 채점한다. | 코드·데이터·설정·호출 한도 고정, 요청 전 시도 저장, 자동 재시도 없음. pending·소스 변경·연결 변조·보고서 덮어쓰기 차단. 오프라인 감사·재현 통과. |

초기의 폭넓은 단어 기반 교체 실험은 개발용 근거 확보를 악화해 실제 호출 전에 제외했다. 채택한 선택기는 직접 요청한 절의 추가와 기존 근거 표현 보존을 요구하지만 의미상 완전성을 보장하지 않는 휴리스틱이다. 실행 기본값, 비교 후보의 출처 5개·6,000자 한도, 원문과 인덱스는 유지했다.

| 같은 기준으로 비교한 페이지 지표 | 이전 답변 재채점 | 개선 후 답변 |
| --- | ---: | ---: |
| 전체 실행 AI 통과 | 17/20 (85%) | 17/20 (85%) |
| 필수 인용 근거 전체 확보 | 12/16 | 14/16 |
| 근거 그룹 확보 | 39/43 | 41/43 |
| 출력 검증 통과 | 19/20 | 20/20 |
| 유효 응답 채점 완료 | 19/19 | 20/20 |
| 답변 불가 문항의 적절한 보류 | 4/4 | 4/4 |
| 답변 가능 문항의 보류 | 0 | 1 (`d10`) |
| 성공 응답 평균 지연시간 | 5.37초 (이전 실행) | 4.21초 |

원래 기준 실행의 **15/20**은 이전 채점 지시의 점수다. 같은 답변을 재채점하면 `d07`·`d15`가 통과로 바뀌어 **17/20**이 된다. 15→17을 구현 개선량으로 주장하지 않는다. 같은 새 채점 기준에서는 `d04`·`d08` 개선과 `d10`·`d12` 악화가 상쇄된다. 검색 선택과 생성 지시를 함께 바꿨으므로 각 효과와 지연시간 차이의 원인을 분리하지 않았다.

남은 증빙과 문제:

- `d07`: 새 답변은 예산 규정을 확보해 결재 전 검토 시점을 명시했다. 그러나 채점기는 이전 답변도 모델이 보지 못한 `R3`와 사례를 사용했다고 설명하면서 통과시켰다. 참고 정답이 근거성 판단에 섞이는 문제가 남았다.
- `d10`: 명시적 결재 금액표가 여전히 빠졌다. 새 답변은 사례 사이를 추정하는 대신 보류했고 전체 실행의 실패로 계수한다. 채점기는 새 지시에도 이전 답변의 사례 보간을 통과시켰다.
- `d11`: 금액표 누락과 질문의 팀장 구간 전제를 다시 입증하도록 요구하는 기준이 남았다. 새 답변은 선결제 불인정·재무팀 검토를 설명하지만 해당 기준으로 실패한다. 검색과 기준 해석을 구분해 검토한다.
- `d12`: 필수 기준은 모두 통과했으나 채점기가 타당한 논리적 결합이라고 인정하면서도 한 문장에 직접 쓰이지 않았다고 감점했다. 동시에 새 첫 claim의 예산 주장에 `S2`가 직접 인용되지 않은 문제도 있다. 채점 일관성과 주장별 출처 완전성을 검토하고 점수를 임의 보정하지 않는다.
- `d04`: 새 인용은 통과했지만 한 번의 실행으로 오류 제거를 증명하지 않는다. 이전 거부 원문은 여전히 없어 정확한 변형을 확인할 수 없다.

실제 **새 답변 20회 + 새 채점 39회 = 59회**를 요청했고 제공업체·채점 오류와 재시도는 없었다. 새 생성 입력/출력은 124,273/9,811토큰, 채점은 348,356/15,000토큰이다. 이전 답변 20개는 생성 없이 재사용했다. 전체 테스트 **439개가 46.05초에 통과**했다(신규 30개). 실제 개발용 문맥 20개는 오프라인 재생과 모두 일치했다. **보호 대상 434개**, 그중 **과거 평가 산출물 427개**를 바이트 단위로 보존했다. 사람 검토는 미완료이며 커밋·푸시·Cloud 변경은 하지 않았다.

다음은 참고 정답이 누락된 검색 근거를 대신하지 못하도록 근거성 채점을 분리하는 설계와 독립적인 사람 판정으로 기준을 점검하는 작업이다. 남은 명시적 규정 검색·주장별 인용 누락을 개선하고 개발용으로 재평가한 뒤 코드·기준을 고정해 최종 평가한다. 최종 20문항은 예약 상태로 유지한다. 과거 87건 복구는 원래 채점 프롬프트와의 호환도 필요하므로 새 복구 계획만 만드는 것으로 충분하지 않다. 과거 선택 재생 명령은 현재 소스 검사로 차단될 수 있으며 원본 기록은 보존하고 현재 재생 결과를 아래에 연결했다.

근거: [오프라인 검색 재생](../eval/results/v3_refinement_checks_20261019/retrieval_replay.json), [소프트웨어 테스트](../eval/results/v3_refinement_checks_20261019/software_tests.json), [실제 비교 보고서](../eval/results/v3_refinement_dev_20261019/report.md), [사례 분석](../eval/results/v3_refinement_dev_20261019/analysis.json), [검증](../eval/results/v3_refinement_dev_20261019/verification.json).

```powershell
# 새 폴더에 오프라인 준비. 기준 실행은 개발용 묶음이어야 한다.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement freeze --source-dir eval/results/v3_dev_20261019_1003 --output-dir eval/results/v3_refinement_new_run --max-calls 59
# 과금: 이 기준 실행에서는 모델 최대 59회. 저장 결과 검사에는 실행할 필요 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement run --output-dir eval/results/v3_refinement_new_run
# 완료한 결과의 오프라인 검사·재현.
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement verify --output-dir eval/results/v3_refinement_dev_20261019
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement report --output-dir eval/results/v3_refinement_dev_20261019
```

### 채점 분리와 규정 선택 보완 — 2026-10-19

사용자가 검토한 변경의 게시와 우선순위 1·2번 개발을 승인했다. `8686fff76349cd1a2b615a5b365c80471941d390`을 `origin/main`에 푸시했고 로컬·추적 브랜치·GitHub 커밋의 일치를 확인했다. 아래 신규 작업은 게시 후 시작하며 해당 커밋에는 포함되지 않는다.

| 작업 | 계획한 동작 | 완료 확인 |
| --- | --- | --- |
| 채점 분리 | 저장 답변을 고정해 정확성과 근거성을 독립 요청으로 평가한다. 근거성 요청에는 질문·답변/주장·실제 검색 근거만 보내며 참고 정답·참고 원문·정확성 판정은 전달하지 않는다. 기존 통합 채점 산출물의 재현성을 유지한다. | 입력 분리·출처/주장 연결 검사, 모호함·오류의 별도 표시, 단계별 시도 저장·호출 한도 테스트. 원본 점수를 수정하지 않고 개발용 논쟁 사례를 점검한다. |
| 규정 선택 보완 | 후보 목록에 이미 있는 결재권한 등 관련 규정의 절을 확보한다. 정답 주석이나 추가 모델·검색 호출을 사용하지 않는다. | 개발용 20문항·알려진 v2 60문항 재생. 기존 전체 근거 확보·출처 수·원문을 보존하고 일반적인 선택 회귀 테스트를 추가한다. |
| 검증 | 단위·회귀 테스트 후 채점 분리의 소규모 실제 검사를 조건 고정해 실행한다. | 과거 산출물과 최종 문항을 보존한다. 관측 결과를 사람 판정·전체 답변 정확도와 구분해 기록한다. |

상태: 두 항목의 구현과 소프트웨어·검색 테스트를 완료했다. 실제 채점 기준 점검은 부분 완료이며 독립 사람 판정이나 새 답변의 정확도 측정은 완료하지 않았다.

- [split_judge.py](../eval/split_judge.py)는 정확성·근거성 요청을 허용한 필드만으로 각각 구성한다. 참고 정답·참고 원문은 근거성 입력에 들어가지 않으며 정확성 요청에는 근거성 판정을 보내지 않는다. 주장별 인용 완전성도 별도 표시한다. 각 주장·채점 항목을 API 응답의 필수 필드로 요구하고, 직접 인용 증빙은 해당 주장의 기존 인용 번호만 선택하게 한다. 검색 근거의 원문 인용 검증은 유지한다.
- [review_split.py](../eval/review_split.py)는 선택한 개발용 저장 답변·코드·프롬프트·설정·요청 한도를 고정한다. 단계별 시도를 저장하고 입력·스키마·원본 답변 연결을 감사한다. 오류는 미확정으로 남기고 pending·성공·실패 요청을 자동 반복하지 않는다. 이전 스키마와 통합 채점 보고서의 감사도 유지한다.
- `query_and_section_topics_v3`는 승인자·결재권자 등 업무 규정 표현을 묶는다. 앞선 검색 결과·기존 질문 본문 근거·이미 확보한 요청 규정 주제를 보존하며, 명시적인 규정 주제를 추가할 때 절 제목의 우연한 글자 겹침은 교체할 수 있다. 마지막 요청 문장을 중심으로 삼되 앞부분의 결재권한 주장은 확인한다. 문항 ID·파일명·금액·정답 주석으로 선택하지 않는다. 넓게 주제를 적용한 초기 실험은 견적 조항을 밀어내 폐기했고 최종 재생에서는 전체 근거 확보 악화가 없었다.

| 검증 | 관측 결과 |
| --- | --- |
| 전체 소프트웨어 테스트 | **483개, 22.25초 통과**, 기존 439개 대비 신규 44개 |
| 개발용 검색 재생 | **14/16→16/16**, `d10`·`d11` 개선, 악화 없음 |
| 알려진 v2 검색 재생 | **48/48→48/48**, 악화 없음 |
| 과거 기록 보존 | 기존 평가 산출물 **515개**를 포함한 **522개 파일** 바이트 동일 |
| 실제 채점 진단 | **10회 요청**, 채택 6개 단계·검증 거부 3개·제공업체 오류 1개, 자동 재시도 없음 |
| 새 답변 / 최종 문항 평가 | **0 / 0** |

초기 세 진단 실행에서 설명용 근거와 직접 인용 증빙 혼용, 주장 판정 누락, 해당 주장이 인용하지 않은 구간 제시가 드러났다. 거부 원문을 모두 보존했고 증빙 필드 분리·항목별 필수 응답 필드·기존 인용 번호 선택으로 보완했다. 마지막 실행은 이전(`before`) 답변 두 개의 네 단계를 채택한 후 개선 후(`after`) 채점 시작에서 `ClaudeError`로 멈췄다. 제공업체 응답 원문을 기록하지 않아 구체적인 API 원인은 알 수 없으며 잔액 부족으로 단정하지 않는다. 계획한 전후 채점 비교는 **완료하지 못했다**. 전체 실행에서 확인한 사용량은 입력 59,734·출력 12,467토큰이며 제공업체 오류의 사용량은 미확인이다.

입력 분리는 검증했지만 AI 의미 판정의 일관성은 해결되지 않았다. 최신 `d07` 판정은 사례 일반화를 설명하면서도 근거성을 통과시키고 인용 완전성을 실패시킨다. `d12`도 정확성·근거성을 통과시키지만 인용 완전성은 실패시킨다. 이는 이전 답변에 대한 보정하지 않은 AI 판단이며 사람 판정이나 새 RAG 답변의 개선 증거가 아니다. 다음은 채점 논쟁의 독립 판정, 추가 유료 검사 전 API 오류 확인, 생성 답변의 주장별 인용 보완 후 새 선택 방식으로 개발용 답변 생성·평가다. 코드·기준을 고정한 뒤 예약한 최종 20문항을 평가한다.

근거: [검색 재생](../eval/results/v3_split_checks_20261019/retrieval_replay.json), [최종 테스트](../eval/results/v3_split_checks_20261019/software_tests_indices.json), [검증](../eval/results/v3_split_checks_20261019/verification.json), [부분 완료 실제 보고서](../eval/results/v3_split_review_indices_20261019/report.md), [사례 분석](../eval/results/v3_split_review_indices_20261019/analysis.json). 앞선 실패 기록은 `v3_split_review_20261019`, `v3_split_review_fixed_20261019`, `v3_split_review_keyed_20261019`에 보존했다.

```powershell
# 오프라인: 저장 시도를 감사하고 부분 완료 보고서를 재현한다. 모델 호출 없음.
.\.venv\Scripts\python.exe -X utf8 -m eval.review_split report --output-dir eval/results/v3_split_review_indices_20261019
```

`verify`는 완료한 실행을 요구하므로 이번 부분 실행을 완료로 인정하지 않는다. 새 유료 실행은 새 조건 고정 계획이 필요하며 중단한 결과는 보존한다. 별도 dev-log가 없어 Phase 변경 이력에 기록한다.

### 제한한 최종 점검 — 2026-10-19

사용자가 남은 범위를 개발 논쟁 사례, 최종 평가 1회, 시연 점검으로 제한했다. 추가 채점기 개발과 과거 미완료 채점 복구는 보류한다. 고정한 기준은 명시된 규칙의 적용은 허용하지만 예시의 일반화는 허용하지 않고, 질문이 요구한 답과 전제의 반복을 구분하며 주장에 붙은 인용을 확인한다. Codex가 원본 PDF를 대조했으며 **에이전트 검토이지 독립적인 사람 판정은 아니다.**

`llm.py`에 허용된 오류 분류와 숫자 HTTP 상태를 제공업체 응답 본문 없이 기록하도록 보완하고 `rag.py`와 저장 답변에 전달했다. 과거 API 오류는 당시 응답이 남지 않아 구체적 원인을 확정할 수 없다. 이번 실행에서는 제공업체 오류가 없었다. 검색·생성 지시는 변경하지 않았다. 기존 오류 테스트를 강화하고 진단 전달 테스트 1개를 추가해 **484개가 18.33초에 통과**했다.

| 항목 | 관측 결과 |
| --- | --- |
| 개발 논쟁·대조 질문 6개 | 요건 충족 5/6; d12는 인용에 표 구분 기호를 넣어 차단 |
| 최종 실행 | 출력 검증 20/20; 생성 20회; 별도 AI 채점 0회 |
| 최종 필수 근거 검색 | 답변 가능한 16개 중 12개 |
| 최종 내용 요건 | 전체 15/20; 답변 가능한 질문만 11/16 |
| 최종 내용·주장별 인용 모두 충족 | 13/20 |
| 답변 불가 질문 | 4/4 올바르게 보류 |
| 초기화 제외 응답 시간 | 평균 5.193초·중앙값 4.341초·최대 11.198초 |
| 전체 새 모델 요청 | 답변 26회·채점 0회·자동 재시도 0회; 비생성 Models API 확인 2회 |
| 26회 전체 토큰 | 입력 163,233 / 출력 17,920; 금액 환산 없음 |
| 시연 | 실답변 저장본 AppTest 재생: 답변 3개·보류 1개·차단 1개; 로컬 HTTP 시작·재시작 통과 |
| 원본 보존 | 기존 파일 554개 동일; 개발·최종 실행의 코드·판정 기준 동일 |

최종 실패를 보존했다. f01·f07·f09는 필수 규정 검색 누락 후 보류, f04는 계약 변경 규정 검색 누락으로 변경 계약서 작성을 빠뜨렸다. f08은 검색·인용에는 있는 계좌 확인 자료를 답변 본문에 명시하지 않았고 f03·f05는 주장 인용에서 금액 기준·검토 시점이 빠졌다. 해당 고정 최종 실행 안에서는 결과를 본 뒤 조정·재실행하지 않았다. 이후에는 아래와 같이 관측한 사례를 회귀 검사로 사용해 보완했으며 원래 점수는 변경하지 않는다. 같은 문서를 공유하는 이 질문들은 이제 관측한 회귀 사례이며, 일반 성능의 증명이나 이전 자동 채점 점수와의 직접 비교 자료가 아니다.

[보고서와 사람 검토용 20문항](../eval/results/v3_closeout_20261019/report.md), [요약](../eval/results/v3_closeout_20261019/summary.json), [검증](../eval/results/v3_closeout_20261019/verification.json), [테스트 출력](../eval/results/v3_closeout_20261019/pytest.txt), [시연 검사](../eval/results/v3_closeout_20261019/demo_check.json)를 보존한다. 일회용 `run.py`는 시도를 보존하고 기존 출력 폴더를 거부하며, 완료한 최종 평가를 반복 실행하는 안내가 아니다. 화면 검사는 실제 답변 저장본 재생이며 HTTP 준비 시간은 모델 초기화나 원격 Cloud 검증과 구분한다. 독립 사람 검토, 특히 f03·f05·f08의 판정 기준 확인은 남아 있다. 제한한 실행·기록은 이 한계를 포함해 완료하고 이후 게시했다. 별도로 승인받은 아래 집중 개선을 이어서 진행했으며 보존한 최종 20문항 실행을 반복하지 않았다. 독립 채점은 보류 사항이며 포트폴리오 종료의 잔여 필수 조건은 아니다. dev-log가 없어 아래 변경 이력에 기록한다.

### 최종 포트폴리오 개선 — 2026-10-19

사용자는 데모 답변 5개를 확인한 뒤 개선 1·2·4번을 승인했다. 복합 검색 추가 개선(3번)은 선택 사항으로 남긴다. 완료한 변경은 다음과 같다.

| 변경 | 동작과 증빙 |
| --- | --- |
| 1. 답변 필수 항목 | 기본·조건부 필수 서류를 본문에 명시하도록 공통 지시를 보완했다. 실제 답변 7개는 답변 가능 6개·올바른 보류 1개이며, 계좌 관련 3개 답변 모두 계좌 확인 자료를 명시했다. [검토](../eval/results/completeness_display_20261019/review.json) |
| 2. 모든 근거 인용 | 출처별 서로 다른 주장 인용을 순서대로 표시하고 떨어진 발췌·과거 저장 답변 호환을 유지한다. 의미 있는 표시 테스트 4개를 추가했다. 첫 AppTest 재생은 답변 7개·출처 영역 11개·인용 23개다. [재생](../eval/results/completeness_display_20261019/display_check.json) |
| 4. 주장별 인용 완전성 | 담당자·금액 기준·시점·예외·예상 기간 단서와 문장 전체·표의 조건을 인용에 보존하도록 지시했다. 최종 금액 경계·검토 시점·명시적 PO 담당자·보류 4사례 통과, 주장 11개·주장 인용 16개를 대조했다. [검토](../eval/results/citation_completeness_20261019/review.json) |

인용 후속은 **답변 호출 10회·별도 채점 0회·자동 재시도 0회**다. 처음 2회는 금액 경계 답변 성공과 기존 2,048토큰 한도의 미완성 응답이며, 그 회차의 나머지 예정 2개는 실행하지 않았다. 4,096토큰에서 명시적으로 검사한 4개는 유효 응답이지만 시점 인용·단서 문제가 남았다. 문장 전체·단서 지시 보완 후 최종 4개는 Codex 원문 대조를 통과했다. 모든 시도와 이전 실패를 보존한다. 앞의 두 개선은 별도의 답변 7회를 사용했으며 두 결과 모두 독립 평가셋이나 새 전체 정확도 측정은 아니다.

기본 출력 상한은 **4,096토큰**이며 검색 1회·최대 생성 1회·30초 제한·자동 재시도 없음은 유지한다. 기존 명시적 설정이 기본값보다 우선한다. 최신 [소프트웨어 기록](../eval/results/citation_completeness_20261019/software_tests.json)과 [테스트 로그](../eval/results/citation_completeness_20261019/final/pytest.txt)는 **488개·72.75초 통과**다. 최종 [Streamlit 재생](../eval/results/citation_completeness_20261019/display_check.json)은 모델 호출 없이 저장 답변 4개·출처 영역 9개·인용 16개를 확인했다. [검증](../eval/results/citation_completeness_20261019/verification.json)은 인용 후속 시작 시점의 기존 파일 621개 보존을 기록한다. 과거 산출물의 게시·설정 필드는 해당 실행 당시 상태로 유지한다.

구현은 [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4)으로 게시했다. 사용자는 이번에 Cloud `ANTHROPIC_MAX_TOKENS=4096` 변경 완료를 보고했으며 이전 pages/5/6000 적용·Reboot도 사용자 보고 기준이다. 최신 게시본에서 새 질문 실행·재시작·실제 설정 조회를 별도로 관측하지 않았다. 사용자의 이전 답변 5개 확인과 로컬 최종 회귀 검사는 구분한다.

합의한 포트폴리오 범위는 완료했다. 원문 일치 검증은 유지하며 의미적 완전성은 생성 지시와 Codex 확인으로 다룬다. 모든 답변에 대한 자동 보장은 아니다. 넓은 모니터 수령 질문의 정산 시점과 다른 기록된 검색 누락은 남아 있고, 독립 사람 채점·과거 채점 87건 및 검토 34건·Phase 7·운영 서비스 검사는 보류한다. 원래 최종 20문항 점수는 유지한다. 이 범위를 종료하기 위한 추가 개발·유료 평가는 필요하지 않다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-16 | 코드 변경 전에 실행 계획 작성. 사용자가 개발·테스트를 승인했다. 별도 dev-log 스킬 미설치로 이 문서에 변경 이력을 기록한다. |
| 2026-10-16 | 선택형 페이지 문맥 검색과 요구 항목·조건 보존 지시 구현. 개발용 검색으로 pages5 선택, 테스트 267개와 실제 답변·AI 채점 각 6건 완료. 증빙 및 README 2개 연결. 로컬 범위 완료이며 Cloud에는 게시하지 않음. |
| 2026-10-16 | b89ed76 코드 푸시 완료와 pages/5/6000 활성화 우선·Phase 7 사용성 보류 결정을 기록했다. Cloud Settings 적용 절차를 준비했으며 관리 도구 연결이 없어 서버 값·활성화는 미확인이다. 문서만 갱신했으며 별도 dev-log는 미설치로 생략했다. |
| 2026-10-16 | 사용자의 설정 변경·Reboot 완료 보고를 기록하고 목표를 RAG 로직·측정된 정확도·정교한 근거 처리·개선 설명으로 명확히 했다. 동시 접속 검사는 제외하고 사용성 보류를 유지했다. 추적·평가를 다음 제안으로 우선했으며 새 원격 검사는 실행하지 않았다. 별도 dev-log 미설치로 문서 이력에 기록했다. |
| 2026-10-16 | 추적 기록·원격 대조 수정 및 실제 LangSmith 검증, 고정한 답변 120회 비교를 완료했다. 일부 채점 실패와 잔액 부족을 확인하고 87건 복구를 오프라인 준비했다. 사용자 결정으로 충전·채점 보류. 최종 테스트 305개 통과·과거 산출물 90개 보존. 로컬 변경이며 별도 dev-log는 미설치로 생략. |
| 2026-10-16 | 검증 규칙·위치 기록과 마지막 페이지 선택 개선. 오프라인 근거 확보 47/48→48/48, 전체 근거 확보 악화 없음. 테스트 347개 통과·기존 파일 336개 보존·87건 복구 계획만 새로 준비. 모델 호출·푸시·Cloud 변경 없음. 별도 dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 공통 데이터셋 검사, 묶음별 버전 2 평가 프로토콜, 호출 계획·유형별 보고서와 PDF 대조한 v3 40문항 구현. 로컬 테스트·과거 산출물 호환 확인. 유료 평가·게시 없음. 별도 dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 사용자 충전 후 모델 79회 호출로 v3 개발용 비교 완료. 원본 AI 통과 14/20·15/20, 인용 검증 실패 1건, 제공업체·채점 오류 없음. 원본 점수·기준 파일을 보존하고 검색 실패·채점 논쟁을 기록했다. 최종 문항·과거 채점 복구·Cloud 변경 없음. dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 절 제목 기반 문맥 선택, 인용·추론 지시, 채점 지시, 저장 답변 비교 도구 구현. 테스트 439개·실제 호출 59회. 근거 12/16→14/16, 유효 출력 19/20→20/20이나 동일 기준 AI 통과는 17/20→17/20. 파일 434개를 보존하고 채점·검색 한계를 기록했다. 최종 평가·게시 대기, dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 검토한 파일 192개를 8686fff로 게시한 뒤 채점 분리·규정 주제 선택을 로컬 구현했다. 테스트 483개, 개발용 근거 14/16→16/16·v2 48/48 유지. 실제 채점은 요청 10회·채택 6개 단계·검증 거부 3개·API 오류 1개로 부분 완료. 파일 522개 보존, 새 답변·최종 평가·독립 판정 대기. dev-log 미설치로 여기에 기록. |
| 2026-10-19 | 제한한 마무리: 안전한 API 진단, 테스트 484개, 개발 6개+최종 20개 생성·별도 채점 없음. Codex 기준 최종 내용 15/20·인용까지 13/20, 원본 554개 보존. 시연 재생·재시작 통과, 사람 검토·게시 미완료. 추가 평가기 개발 보류, dev-log 미설치. |
| 2026-10-19 | 개선 1·2·4 완료, 테스트 488개, 필수 항목 확인 7회, 인용 후속 전체 10회·최종 4사례 통과를 기록했다. 실패·과거 점수 보존. 게시본 175bda7·사용자 보고 4096토큰 설정을 반영하고 합의 범위를 완료로 정리했다. 이번에는 문서만 변경, dev-log 미설치. |
