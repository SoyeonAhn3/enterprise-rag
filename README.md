[English](README.md) | [한국어](README_ko.md)

# Enterprise RAG Assistant

A portfolio project for answering questions about business policies with retrieval-augmented generation (RAG). The Streamlit app searches a fixed PDF collection, generates Korean answers from retrieved evidence, and displays the source document, page, and excerpt.

The goal is to deliver a public Streamlit demo, source code, and measured evaluation results under the scope of a two-day MVP plan.

## Measured results

The original answer evaluation on **2026-10-14** used **4 synthetic Korean PDFs, 13 pages, 22 chunks, and 10 questions**. Automated checks were rerun on **2026-10-16**.

| Measure | Recorded result | What was checked |
| --- | --- | --- |
| Retrieval Hit@3 | **8/8 (100%)** | At least one accepted evidence page in the top three chunks for each answerable question |
| Multi-document page coverage | **2/2** | All required evidence groups had an accepted page among the retrieved chunks |
| Abstention on unanswerable questions | **2/2** | Questions without a documented answer received an abstention |
| AI-agent-reviewed correctness | **9/10 (90%)** | Grading against reference answers and criteria, including two correct abstentions |
| Mean RAG response time | **3.33 seconds** | Retrieval and answer generation; model/index/client initialization excluded |
| Automated tests | **243 passed** | Program and failure checks on 2026-10-16, separate from answer evaluation |

Correctness was reviewed by an AI agent; **human grading has not been completed**. The answerable subset scored **7/8 (87.5%)**. These figures describe this small synthetic benchmark. The q08 answer omitted required detail despite supported conclusions; the [failure analysis](Phase/Phase5_EvaluationAndDeployment.md) records this limitation.

Inspect the [original evaluation run](eval/results/phase5_baseline.json), [baseline metrics](eval/results/phase5_metrics.json), [AI review](eval/results/phase5_agent_review.json), and [243-test verification record](eval/results/phase5_v2_20261014/verification_20261016.json) for the supporting evidence.

The expanded evaluation also completed on 2026-10-14: **60 questions, 120 saved answers, and 120 AI grades**. Development-only retrieval selected B (800 characters / 120 overlap / k=5) for comparison with A (800/120/3). The app still defaults to k=3.

| Split | A AI correctness | B AI correctness |
| --- | --- | --- |
| Development, 40 questions | 35/40 (87.5%) | 39/40 (97.5%) |
| Final check, 20 questions | 13/20 (65.0%) | 15/20 (75.0%) |

The same Claude model generated and graded answers in separate calls; human review remains pending. The [expanded report](eval/results/phase5_v2_20261014/report.md) includes failure analysis, checkpoint recovery, and a 34-entry review queue. On 2026-10-15, offline verification reproduced the metrics from the saved artifacts. Reports now expose failed/missing answers, handle zero successful responses, and protect human notes in the review CSV.

```powershell
# Read-only validation; no model calls or credentials required.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
```

## Current status

**Phases 1–4 work locally. Phase 5 evaluation, tracing integration, and deployment preparation are implemented; public deployment and a real LangSmith trace remain pending.**

The [2026-10-16 status audit and development roadmap](Phase/DevelopmentStatusAndRoadmap.md) links current code and verification evidence to the remaining work: finish public deployment and tracing, then improve retrieval quality, followed by optional usability and enterprise expansion. The audit reran 243 tests, reproduced saved metrics, and validated the deployment bundle without new model calls.

| Available now | Details |
| --- | --- |
| MVP specification | Requirements, architecture, implementation sequence, and acceptance criteria |
| Sample documents | Four Korean PDFs totaling 13 pages |
| Evaluation dataset | Original ten-question baseline plus 60-question v2 with separate development/final splits |
| Offline preprocessing | Four PDFs / 13 pages produce 22 chunks with source metadata |
| Indexing and retrieval | Persistent Chroma, compatible-index reuse, explicit rebuilds, and top-three retrieval |
| Local verification | 243 tests passed; includes artifact consistency, failure/missing-answer reporting, human CSV preservation, and existing RAG/UI/deployment checks |
| Real model retrieval | Local E5 model; q01/q07/q08 all cover their required evidence groups, including the original quotes |
| Grounded answers | `RAGAssistant.answer()` uses one retrieval and at most one Claude call; returns cited claims, original retrieval, and latency |
| Live Claude checks | q01/q07/q08 answered with matched quotes; q09/q10 abstained; partial/conflicting evidence and document instructions checked |
| Streamlit UI | Examples, chat history, source expanders, safe errors, and a ten-attempt session limit; three real browser questions verified |
| Phase 5 evaluation | Original baseline plus 120 paired answers/AI grades, reproducible metrics, and 34 pending human-review entries |
| Deployment preparation | Portable precomputed-vector bundle and server settings; [deployment guide](DEPLOYMENT.md), public URL pending |
| Development phases | Five bilingual phase documents plus a current status audit and prioritized roadmap |

`app.py` uses the verified `rag.py` pipeline; `grounding.py` validates claims and citations. `eval/evaluate.py` preserves the ten-question baseline, while `eval/benchmark.py` compares settings and verifies the expanded run. `tracing.py` isolates optional LangSmith failures. See the [Phase 4](Phase/Phase4_StreamlitInterface.md) and [Phase 5 reports](Phase/Phase5_EvaluationAndDeployment.md) for current evidence. Source repository: [SoyeonAhn3/enterprise-rag](https://github.com/SoyeonAhn3/enterprise-rag). **No public demo URL has been verified.**

## Run locally

With Python 3.12 and Git installed, use PowerShell to clone the project and install the runtime dependencies:

```powershell
git clone https://github.com/SoyeonAhn3/enterprise-rag.git
Set-Location enterprise-rag
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

Set `ANTHROPIC_API_KEY` in the local `.env`, then run these commands from the repository root. Keep an existing `.env` and its settings. The app imports the bundled vectors automatically and downloads the public query-embedding model on its first start; building a document index is optional for this fixed corpus.

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Open the local URL printed by Streamlit and try a sample question. Answer generation uses the operator's Claude key and incurs API usage. Visitors do not enter credentials. For server settings and public deployment checks, follow [DEPLOYMENT.md](DEPLOYMENT.md).

### Offline checks and development

These checks use local documents, saved evaluation results, and test doubles. They require no API credentials or new model calls:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
```

The dry run creates `data/chunks_preview.json` without API credentials or embedding requests. The current corpus produces **4 documents, 13 text pages, 0 skipped pages, and 22 chunks**. The preview is generated locally and excluded from Git.

### Indexing and command-line answers

Indexing and retrieval need no API key. The first run downloads the public `intfloat/multilingual-e5-small` model into `data/embedding_models/` (about 487 MB locally); subsequent runs reuse it on CPU. Both `.env` and the model cache are ignored by Git.

```powershell
# No API key needed. The first build downloads the local model.
.\.venv\Scripts\python.exe -X utf8 ingest.py
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
.\.venv\Scripts\python.exe -X utf8 -m eval.check_retrieval
```

Use `ingest.py --rebuild` when PDFs, embedding model/dimensions, or chunk settings change, including migration from an old OpenAI index. A matching index is reused without loading the embedding model or embedding documents again. The default local model produces 384-dimensional vectors with `passage: ` and `query: ` prefixes. Configuration priority is environment → supplied server secrets → `.env` → defaults. After the initial download, set `EMBEDDING_LOCAL_FILES_ONLY=true` for offline loading; leave it `false` on a new machine until the model is cached.

The smoke check writes `data/retrieval_smoke.json` for q01/q07/q08, retaining all retrieved chunks and separately checking source pages and evidence quotes. The real local model passed all three checks, including offline fresh-process reload with document embedding disabled. For the fixed offline workflow, stop the application before rebuilding and restart its retriever afterwards; old inactive collections remain stored and are not queried.

Set `ANTHROPIC_API_KEY` locally for Claude, then run `.\.venv\Scripts\python.exe -X utf8 llm.py --check`. This checks model access without generating an answer. `ANTHROPIC_MODEL` defaults to `claude-sonnet-5-5`; calls have a 30-second timeout, zero automatic retries, and a configurable output limit of 2048 tokens by default. An OpenAI key cannot be used as a Claude key. [Anthropic does not provide embeddings](https://platform.claude.com/docs/en/build-with-claude/embeddings), so local search remains independent of Claude credentials.

```powershell
# One grounded answer; requires the configured Claude key and incurs API usage.
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# Five live questions; saves the complete result to data/answer_smoke.json.
.\.venv\Scripts\python.exe -X utf8 -m eval.check_answers
```

Without `--answer`, `rag.py` keeps its retrieval-only behavior. For Python integration, use `RAGAssistant(retriever, client).answer(question)` and close the caller-owned `Retriever` and `ClaudeClient` when finished; a full example is in the [Phase 3 report](Phase/Phase3_GroundedAnswers.md). Results include `answer`, `answerable`, claim-level quotes, validated `sources`, all `retrieved_chunks`, and search/generation/total latency. Initialization time is excluded.

Insufficient evidence returns exactly `등록된 문서에서 해당 정보를 확인할 수 없습니다.` with no cited sources. Provider failures and invalid output raise distinct exceptions instead of becoming successful abstentions. Quotes must match the retrieved text, ignoring whitespace only; filenames/pages come from stored metadata. Matching quotes establishes provenance, while semantic correctness still requires review.

## Start with the project materials

For the local chat interface, run:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

The server reads `.env` or Streamlit Secrets. Visitors never enter a key. On a fresh checkout, the app imports `deployment/index_bundle.json` without embedding documents, then downloads the public local query model once. A cached resource reuses the model/index/client. Each session allows ten attempts by default, including failures; provider-level budget controls are still needed for public sharing.

![Local Streamlit home screen](docs/evidence/local-home.png)

The [chat screenshot](docs/evidence/local-chat.png) shows real local answers, source excerpts, and abstention. Public Cloud setup, secrets, restart checks, and optional trace verification are described in [DEPLOYMENT.md](DEPLOYMENT.md).

Source excerpts reconnect PDF-split Korean words when their complete form is found in the fixed documents, and use word-based wrapping. Original evidence is retained. The [line-wrap fix report](Phase/Phase4_StreamlitInterface.md#source-excerpt-line-wrapping--2026-10-14) includes desktop/mobile screenshots and regression results.

1. Read the [MVP plan](plan/enterprise_rag_assistant_streamlit_mvp_plan.md) for the implementation requirements and planned deployment workflow.
2. Review the [sample-document guide](rag_mvp_sample_documents/README.md) for corpus details and evidence-matching rules.
3. Inspect the [runtime evaluation dataset](eval/questions.json) for the questions, reference answers, and grading criteria. The reviewed original remains in the sample-document folder.

The plan, document guide, PDFs, and evaluation content are written in Korean.

## Sample documents

The corpus describes purchasing, approvals, IT security, contracts, and settlement at the fictional company **Gaonbiz (가온비즈)**. All four documents use version `1.0` and the effective date `2026-09-01`.

| Document | ID | Pages | Coverage |
| --- | --- | ---: | --- |
| [Purchase requests and ordering](rag_mvp_sample_documents/01_purchase_process.pdf) | GB-PUR-01 | 3 | Requests, comparison quotes, purchase orders, and emergency purchases |
| [Approval authority and budget controls](rag_mvp_sample_documents/02_approval_budget.pdf) | GB-APR-02 | 3 | Approval thresholds, budget reviews, and aggregation of related purchases |
| [IT assets and SaaS security reviews](rag_mvp_sample_documents/03_it_security.pdf) | GB-SEC-03 | 3 | Prior security reviews, free trials, review timelines, and asset registration |
| [Contracts, acceptance, and settlement](rag_mvp_sample_documents/04_contract_settlement.pdf) | GB-CON-04 | 4 | Legal reviews, delivery acceptance, payment documents, and settlement schedules |

These are synthetic demonstration documents. Their policies and monetary thresholds do not describe a real company's rules and must not be used for actual purchasing or contracts.

## MVP architecture

The implemented pipeline uses **2-Step RAG: one retrieval step followed by answer generation**.

1. Extract each PDF page, split its text, and retain `source_file`, `page`, and `chunk_id` metadata.
2. Generate document embeddings and build a fixed Chroma index before deployment.
3. Embed a user's question and retrieve the top three relevant chunks.
4. Generate a Korean answer from the retrieved evidence, or abstain when the evidence is insufficient.
5. Display validated source references with filenames, 1-based page numbers, and excerpts.
6. Record retrieval and generation traces, then evaluate the application against the prepared questions.

Initial chunking settings are approximately **800 characters per chunk** with **120 characters of overlap**. These are starting settings from the plan, not measured optimal values.

| Area | Technology / status |
| --- | --- |
| Application and UI | Python, Streamlit |
| PDF extraction | PyMuPDF |
| RAG pipeline and chunking | LangChain, langchain-text-splitters |
| Vector index | Chroma, langchain-chroma |
| Embeddings | FastEmbed / ONNX Runtime, local multilingual E5 |
| Answer generation | Anthropic Claude API, official Python SDK |
| Tracing | LangSmith integration implemented; real remote trace pending |
| Evaluation | Python, JSON, AI grading; human review pending |
| Deployment | Streamlit Community Cloud planned; public verification pending |

The application is verified locally on Windows / Python 3.12.10 with pinned dependencies. Streamlit 1.65.0 was added without replacing existing packages; `pip check` passes. LangSmith HTTP contracts and disabled/failing tracing are tested, but the real trace needs an operator key. Cloud compatibility, memory, model-cache startup, and public restart behavior remain unverified. The Linux Docker daemon was unavailable locally.

## Evaluation design

The original dataset contains **six single-document questions, two multi-document questions, and two unanswerable questions**. It covers amount boundaries, deadlines, approval and review requirements, and abstention. The separate [v2 dataset](eval/questions_v2.json) expands to 40 development and 20 final-check questions under the [Phase 5 protocol](Phase/Phase5_EvaluationAndDeployment.md).

Each answerable question has `evidence_groups` for the facts needed to answer it. Groups are combined with **AND**; candidates within a group's `any_of` are combined with **OR**. Each candidate records `document`, `page`, and an original `quote`. A valid alternative source is accepted without requiring every alternative page.

For example, q07 requires both an approval-authority source and a security-review source. The security requirement can be supported by page 1 or page 3 of `03_it_security.pdf`.

| Original baseline measure | Definition |
| --- | --- |
| Retrieval Hit@3 | Among the eight answerable questions, the proportion with at least one accepted document/page in the top three retrieved chunks |
| Multi-document Coverage | For each of the two multi-document questions, whether every required evidence group has at least one candidate page in the top three |
| Answer Correctness | Manual assessment of all ten answers using the reference answers and `grading_criteria`, including whether key claims are supported by retrieved evidence |
| Abstention | Whether the application appropriately declines to answer the two questions whose answers are absent from the corpus |
| Latency | Mean response time across the ten questions |

Page matches alone do not establish that the relevant passage was retrieved. The actual chunks must also be reviewed for supporting evidence. `answer_keywords` are review aids, not an automatic correctness test.

**Do not index the evaluation dataset or send reference answers, evidence annotations, or grading criteria to generation.** A check forwards only the current question to RAG; retrieved PDF text supplies the evidence. Unanswerable questions have empty `evidence_groups`; they are excluded from retrieval and multi-document coverage measures, and an empty list does not count as successful evidence retrieval.

The Phase 2 smoke check measured q01/q07/q08 with real local E5. Phase 5 now records all ten questions below. This small synthetic dataset does not establish performance on real enterprise documents.

The [2026-10-14 baseline](eval/results/phase5_baseline.json) used `claude-sonnet-5-5` and the unchanged 22-chunk index. All ten requests completed without error. [Agent review](eval/results/phase5_agent_review.json) is explicitly distinguished from the pending [human review](eval/results/phase5_human_review.template.json).

| Measured result | Value |
| --- | --- |
| Retrieval Hit@3 / multi-document coverage | 8/8 / 2/2 |
| All required reference quotes retrieved | 8/8 |
| Unanswerable-question abstention | 2/2 |
| Mean RAG latency | 3326.96 ms, initialization excluded |
| Agent-reviewed correctness / grounding | 9/10 / 10/10 |

q08 gives the supported CFO/legal-review conclusion but omits the general threshold and explicit timing required by the full rubric. Those general clauses were not retrieved. It is recorded as incorrect under that rubric, rather than turning retrieval success into a correctness claim. No reference answers are sent to the model. See the [Phase 5 analysis](Phase/Phase5_EvaluationAndDeployment.md).

```powershell
# Ten new billable requests; checkpointed results use a new timestamped filename.
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate
# Offline recomputation; no API calls.
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate --report eval/results/phase5_baseline.json --review eval/results/phase5_agent_review.json
```

For tracing, set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` locally, then run `python -m eval.check_trace` with the project virtual environment. Missing/failed tracing does not block answers; the verifier requires remote retrieval/generation runs. The key and actual trace are currently absent.

## Development sequence and scope

The [MVP plan](plan/enterprise_rag_assistant_streamlit_mvp_plan.md) defines the scope. Phase 4 is locally complete. Phase 5 stays in progress while real tracing and public deployment checks remain unverified. Full human grading is deferred under the decision recorded in Phase 5 and remains explicitly unverified. The [current roadmap](Phase/DevelopmentStatusAndRoadmap.md) details remaining release work and proposed later milestones.

| Phase | Goal | Status |
| --- | --- | --- |
| [1 — Foundation](Phase/Phase1_Foundation.md) | Verify the environment, fixed corpus, page metadata, and chunking | ✅ Completed; 35 tests passed |
| [2 — Indexing and retrieval](Phase/Phase2_IndexingAndRetrieval.md) | Build/reload a Chroma index and retrieve the top three chunks | ✅ Completed with real local embeddings |
| [3 — Grounded answers](Phase/Phase3_GroundedAnswers.md) | Generate supported answers, validate sources, and abstain | ✅ Completed with live Claude checks |
| [4 — Streamlit interface](Phase/Phase4_StreamlitInterface.md) | Provide chat, source display, loading/errors, and usage controls | ✅ Local browser verified |
| [5 — Evaluation and deployment](Phase/Phase5_EvaluationAndDeployment.md) | Preserve the ten-question baseline, compare 60 questions, verify tracing, and publish the demo | 🚧 Expanded AI evaluation and offline verification complete; human review and remote checks pending |

The original two-day target maps Phases 1–4 to local operation on Day 1 and Phase 5 to evaluation/deployment on Day 2. Completion is based on verification evidence, not elapsed time. Each Phase document contains English first and Korean second.

The MVP uses a fixed corpus. User uploads, OCR, complex table recognition, authentication and document permissions, agentic or repeated retrieval, hybrid search, reranking, and long-term memory are outside the current scope.

## Current project structure

```text
Enterprise-rag/
├── Phase/
│   ├── DevelopmentStatusAndRoadmap.md       # Current audit and prioritized next work
│   ├── Phase1_Foundation.md                 # ✅ Completed
│   ├── Phase2_IndexingAndRetrieval.md       # ✅ Local model acceptance complete
│   ├── Phase3_GroundedAnswers.md            # ✅ Grounded answers verified
│   ├── Phase4_StreamlitInterface.md         # ✅ Local browser verified
│   └── Phase5_EvaluationAndDeployment.md    # 🚧 Remote completion gates pending
├── .streamlit/                             # Theme and server-secret template
├── deployment/index_bundle.json            # Reviewed portable precomputed vectors
├── docs/evidence/                          # Actual local browser screenshots
├── documents/                              # Four runtime PDFs
├── eval/
│   ├── __init__.py
│   ├── check_retrieval.py                  # q01/q07/q08 retrieval smoke check
│   ├── check_answers.py                    # Five live grounded-answer checks
│   ├── evaluate.py                         # Ten-question runner and offline metrics
│   ├── benchmark.py                        # Paired evaluation, summarize, read-only verify
│   ├── ai_review.py                        # Reference-based AI grading and pilot
│   ├── expanded_cases.py                   # Versioned dataset and PDF-reference checks
│   ├── render_report.py                    # Verified Markdown/CSV exports
│   ├── check_trace.py                      # Read back actual LangSmith child runs
│   ├── results/                            # Baseline, metrics, agent/human review files
│   ├── questions.json                      # Original ten evaluation questions
│   └── questions_v2.json                   # 40 development / 20 final-check questions
├── plan/
│   └── enterprise_rag_assistant_streamlit_mvp_plan.md
├── rag_mvp_sample_documents/                # Reviewed source materials
├── tests/
│   ├── __init__.py
│   ├── fakes.py                            # Isolated test embeddings
│   ├── test_ingest.py
│   ├── test_config_and_embeddings.py
│   ├── test_claude.py
│   ├── test_index_and_retrieval.py
│   ├── test_retrieval_checks.py
│   ├── test_grounding.py
│   ├── test_answers.py
│   ├── test_answer_checks.py
│   ├── test_evaluation.py
│   ├── test_benchmark.py
│   ├── test_benchmark_artifacts.py
│   ├── test_tracing.py
│   ├── test_deployment.py
│   ├── test_app.py
│   └── test_source_display.py
├── app.py                                  # Korean Streamlit chat interface
├── app_runtime.py                          # Cached RAG resources and lifecycle
├── source_display.py                       # Evidence-preserving excerpt presentation
├── config.py
├── embeddings.py
├── deployment.py                           # Export/import/check portable index
├── tracing.py                              # Optional LangSmith spans
├── grounding.py                            # Prompt, strict JSON, citation validation
├── llm.py                                  # Claude backend and connection check
├── index_store.py
├── ingest.py                               # Preview, index build/reuse, rebuild
├── rag.py                                  # Retrieval and grounded answers (--answer)
├── .env.example
├── .gitignore
├── .python-version
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── DEPLOYMENT.md                           # English/Korean deployment instructions
└── README_ko.md
```

`documents/` and `eval/questions.json` are runtime copies of the reviewed sample materials. Keep them aligned when data changes. Credentials, generated previews/check results, model downloads, the local Chroma database, and the virtual environment are excluded from Git.
