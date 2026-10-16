🌐 [한국어](./README_ko.md) | [English](./README.md)

# Enterprise RAG Assistant

> Ask questions about company policy PDFs and get Korean answers with verified source citations.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Open%20App-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://enterprise-rag-demo-project.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.65-FF4B4B?logo=streamlit&logoColor=white)
![Claude](https://img.shields.io/badge/LLM-Claude-D97757?logo=anthropic&logoColor=white)
![Chroma](https://img.shields.io/badge/Vector%20DB-Chroma-327EFF)

> 🚀 **Try it now:** **[enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/)** — no sign-up or API key needed.
> If the app is asleep, click **"Yes, get this app back up!"** and wait about a minute.

## Overview

**Problem.** Policy questions such as *"If a purchase is exactly ₩1,000,000 excluding VAT, who gives final approval?"* often depend on exact thresholds and conditions spread across several documents. An LLM answering from memory can invent rules or drop conditions.

**Approach.** The app retrieves evidence from a fixed set of PDFs, asks Claude to answer only from that evidence, and checks every cited quote against the retrieved text before showing it. When the documents do not contain the answer, it declines to answer.

**Purpose.** This is a portfolio project. It demonstrates RAG understanding and implementation, **measured** accuracy, precise evidence handling, and explainable improvements. Streamlit is the demonstration interface; usability expansion and concurrent-user testing are outside the current scope. All documents are synthetic policies of a fictional company, **Gaonbiz (가온비즈)**:

| Document | Pages | Topics |
| --- | ---: | --- |
| [Purchase requests and ordering](rag_mvp_sample_documents/01_purchase_process.pdf) | 3 | Requests, comparison quotes, purchase orders, emergency purchases |
| [Approval authority and budget controls](rag_mvp_sample_documents/02_approval_budget.pdf) | 3 | Approval thresholds, budget reviews, split-purchase rules |
| [IT assets and SaaS security reviews](rag_mvp_sample_documents/03_it_security.pdf) | 3 | Prior security reviews, free trials, asset registration |
| [Contracts, acceptance, and settlement](rag_mvp_sample_documents/04_contract_settlement.pdf) | 4 | Legal reviews, delivery acceptance, payment schedules |

![Local Streamlit home screen](docs/evidence/local-home.png)

## Table of Contents

- [How It Works](#how-it-works)
- [Evaluation Results](#evaluation-results)
- [Tech Stack](#tech-stack)
- [AI Components](#ai-components)
- [Quick Start](#quick-start)
- [Tests](#tests)
- [Project Structure](#project-structure)
- [Current Status](#current-status)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Documentation](#documentation)

## How It Works

The pipeline is **2-step RAG**: one retrieval step, then one answer-generation call.

```text
[Before deployment]  4 PDFs
        ↓  ingest.py: extract text per page (PyMuPDF), split into ~800-char chunks with 120-char overlap
     22 chunks, each tagged with source_file · page · chunk_id
        ↓  embed with a local multilingual E5 model, store in Chroma (shipped as a precomputed bundle)

[Per question]  User question in the Streamlit chat
        ↓  rag.py: embed the question and retrieve the top-k chunks
        ↓  (optional page mode: up to 5 distinct whole pages within a 6,000-char budget)
        ↓  grounding.py + llm.py: one Claude call returns JSON claims, each with a quote and source ID
        ↓  Validation: each quote must match the retrieved text; file names and pages come from stored metadata
     Korean answer + sources (document · page · excerpt), or the abstention message
```

## Evaluation Results

All figures come from a **small synthetic benchmark** (4 PDFs, 13 pages, 22 chunks). Correctness was graded by an AI agent; **human review is still pending**.

| Evaluation | Questions | Setting compared | Result |
| --- | --- | --- | --- |
| Original baseline (2026-10-14) | 10 | chunks, k=3 | Retrieval Hit@3 **8/8** · abstention **2/2** · AI-graded correctness **9/10** · mean latency **3.33 s** |
| Expanded, development split (2026-10-14) | 40 | chunks, k=3 → k=5 | AI-graded correctness **35/40 → 39/40** |
| Expanded, final-check split (2026-10-14) | 20 | chunks, k=3 → k=5 | AI-graded correctness **13/20 → 15/20** |
| Page-context retrieval (2026-10-16) | 32 answerable development questions | chunks k=3 → chunks k=5 → pages k=5 | Complete required evidence retrieved **24/32 → 26/32 → 32/32**; known regression cases AI-graded **6/6** |
| Frozen paired comparison (2026-10-16) | 60 (48 answerable) | chunks k=5 → pages k=5 | Complete required evidence in context **37/48 → 47/48** · validated responses **59/60 → 57/60** · answer accuracy **not established** |
| Final-page selection (2026-10-16, offline) | Same 60 known questions | Original pages k=5 → constrained query coverage | Complete required evidence **47/48 → 48/48** · no complete-evidence regressions · no new answers or grades |

The [latest implementation](Phase/Phase6_RetrievalAndAnswerQuality.md#validation-diagnostics-and-evidence-selection) adds safe validation-rule/field-location records and changes only the final page slot when it can cover more question terms without losing the old slot's unique query features. q51 now includes the account-change clause at candidate rank 9. This known-case retrieval result does not establish answer accuracy. The four old errors lack the original diagnostics and remain unexplained.

How to read these numbers:

- **Do not read the 90% baseline alone.** On the 20-question final-check split, correctness was 65% (k=3) and 75% (k=5).
- **Page mode improves retrieval, but its answer accuracy is still unknown.** The frozen comparison has 120 review records: 29 completed, 87 failed, and 4 were skipped after validation errors. A separate provider diagnostic confirmed insufficient credit. The owner deferred the remaining grading. The saved answers and an offline recovery plan let grading resume without regenerating answers. Do not read the partial pass counts as an accuracy rate.
- **The same Claude model generated and graded the answers**, in separate calls. A queue of 34 entries is waiting for human review.
- **These are known cases, not an independent test.** All 60 expanded questions were inspected during development, so the Phase 6 results are diagnostics, not an accuracy estimate. Page mode used 34.39% more context characters on average than chunks/k=5.
- **Reference answers never reach answer generation.** Only the question goes into the pipeline; reference answers, evidence annotations, and grading criteria are used only for scoring.

Evidence: [baseline run](eval/results/phase5_baseline.json) · [AI review](eval/results/phase5_agent_review.json) · [60-question report](eval/results/phase5_v2_20261014/report.md) · [page-context report](eval/results/phase6_20261016/report.md) · [frozen comparison report](eval/results/phase6_quality_20261016/report.md) · [recovery plan](eval/results/phase6_review_recovery_selection_20261016/plan.json)

To verify the saved results offline, without model calls or credentials:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/phase6_quality_20261016
.\.venv\Scripts\python.exe -X utf8 -m eval.selection verify --output-dir eval/results/phase6_selection_20261016
```

## Tech Stack

| Technology | Role | Why |
| --- | --- | --- |
| Python 3.12 | Runtime for app, pipeline, and evaluation | One language from PDF processing to UI; dependencies pinned and checked with `pip check` |
| Streamlit 1.65 | Chat UI and server | UI and server code in one Python app, so no separate backend or frontend is needed |
| Streamlit Community Cloud | Hosting for the public demo | Deploys straight from the GitHub repository; the API key stays in server secrets |
| PyMuPDF | PDF text extraction | Extracts text-based PDFs page by page, so citations keep accurate page numbers without OCR |
| LangChain (core, text-splitters, langchain-chroma) | Document and embedding interfaces, recursive chunking, Chroma wrapper | Standard interfaces let the local embedding model plug into Chroma; chunk settings are recorded in the index signature |
| FastEmbed + ONNX Runtime, `intfloat/multilingual-e5-small` | Document and query embeddings (384 dimensions) | Runs locally on CPU without an API key and supports Korean; Anthropic does not provide an embeddings API |
| Chroma | Persistent vector index | Local file-based index; reused when its signature matches, rebuilt only on request |
| Anthropic Claude API (`claude-sonnet-5-5` by default) | Answer generation and AI grading | Generates Korean answers grounded in the evidence; the model can be changed via `ANTHROPIC_MODEL` |
| LangSmith | Optional tracing of retrieval and generation | Records question, context, prompt, answer, settings, and token usage per run; tracing failures never block answers |
| pytest | Automated tests | Uses test doubles, so the suite runs without credentials or model calls |

## AI Components

| Step | Input | Output | Performed by |
| --- | --- | --- | --- |
| Embedding | Chunk text or question | 384-dimensional vector | Local E5 model (`passage: ` / `query: ` prefixes) |
| Answer generation | Question + retrieved evidence | JSON with answer, answerable flag, and claims with quotes and source IDs | Claude, at most one call per question |
| AI grading (evaluation only) | Answer + reference answer + grading criteria | Grade and reviewer note | Claude, in a separate call |

**Rule-based parts.** PDF extraction, chunking, similarity search, page-context assembly (duplicate pages removed, whole pages only, never truncated), quote validation (match ignores whitespace only), and source metadata. The model never supplies file names or page numbers.

**Model selection.** Set `ANTHROPIC_MODEL` for answers and `EMBEDDING_MODEL` for embeddings. Changing the embedding model requires `ingest.py --rebuild`.

**Failure handling.**
- Insufficient evidence returns exactly `등록된 문서에서 해당 정보를 확인할 수 없습니다.` with no sources.
- Invalid JSON, unknown source IDs, or quotes that do not match the evidence are rejected, and no answer is shown.
- Claude calls use a 30-second timeout and no automatic retries. Provider errors are raised separately from abstentions, and the UI shows a safe error message.
- Evaluation runs never retry automatically. Failed or skipped records stay in the denominators.

**What the output means.** Answers are reference information drawn from synthetic documents. A matching quote proves where a claim came from, not that the answer is complete. Answers can still miss conditions, as the [Phase 5 failure analysis](Phase/Phase5_EvaluationAndDeployment.md) shows.

## Quick Start

### Prerequisites

- Python 3.12 and Git. Commands below use Windows PowerShell.
- An Anthropic API key for answer generation. Retrieval and indexing need no key.
- About 487 MB of disk space for the embedding model, downloaded on first start.

### Install

```powershell
git clone https://github.com/SoyeonAhn3/enterprise-rag.git
Set-Location enterprise-rag
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

### Configure

Set `ANTHROPIC_API_KEY` in `.env`. Other settings are optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | (empty) | Required for answers |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | Claude model for answers |
| `RAG_TOP_K` | `3` | Number of retrieved chunks or pages |
| `RAG_RETRIEVAL_MODE` | `chunks` | Set to `pages` for page-context retrieval |
| `RAG_CONTEXT_MAX_CHARS` | `6000` | Context budget in page mode |
| `EMBEDDING_LOCAL_FILES_ONLY` | `false` | Set to `true` after the first download to load the model offline |
| `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` | `false`, (empty) | Optional tracing |
| `SESSION_QUESTION_LIMIT` | `10` | Question attempts per session, including failed ones |

Settings are read in this order: environment variables → Streamlit secrets → `.env` → defaults. See [`.env.example`](.env.example) for the full list.

### Run

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Open the local URL that Streamlit prints. On first start, the app imports the bundled vectors from `deployment/index_bundle.json` and downloads the query-embedding model, so you do not need to build an index. Each answer uses your Claude key and incurs API usage.

### Command line (optional)

```powershell
# Build or reuse the local index (no API key). Use --rebuild after changing PDFs, embedding model, or chunk settings.
.\.venv\Scripts\python.exe -X utf8 ingest.py
# Retrieval only (no API key)
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# Grounded answer (uses the Claude key)
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# Check Claude access without generating an answer
.\.venv\Scripts\python.exe -X utf8 llm.py --check
# Check LangSmith tracing configuration only (no network or model calls)
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace --preflight --retrieval-mode pages --top-k 5 --context-max-chars 6000
```

For the live trace check, Streamlit Community Cloud setup, secrets, and page-mode activation, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
# Preview chunking without embeddings or API calls (writes data/chunks_preview.json)
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
```

The latest recorded run on 2026-10-16 passed **347 tests** ([verification record](eval/results/phase6_selection_20261016/verification.json)). They cover ingestion, retrieval, page context, grounding validation, the UI, trace hierarchy and token usage, frozen-evaluation and review-recovery safeguards, and deployment. Tests use test doubles and make no model calls. They check software behavior, not answer accuracy.

## Project Structure

```text
Enterprise-rag/
├── app.py                    # Streamlit chat UI (Korean)
├── app_runtime.py            # Cached model, index, and client shared across sessions
├── rag.py                    # Retriever and RAGAssistant; CLI for retrieval or --answer
├── retrieval_context.py      # Page-context assembly within a character budget
├── grounding.py              # Answer prompt, strict JSON parsing, quote and citation checks
├── llm.py                    # Claude client and --check connection test
├── ingest.py                 # PDF extraction, chunking, index build/reuse, --rebuild, --dry-run
├── embeddings.py             # Local FastEmbed E5 embeddings
├── index_store.py            # Chroma index with signature and integrity checks
├── config.py                 # Settings loader
├── deployment.py             # Export, import, and check the portable vector bundle
├── tracing.py                # Optional LangSmith spans with settings and token usage
├── source_display.py         # Source excerpt formatting for the UI
├── documents/                # The 4 PDFs used at runtime
├── deployment/               # Precomputed vector bundle (index_bundle.json)
├── eval/                     # Question sets, evaluation runners, trace check, AI grading, saved results
├── tests/                    # pytest suite
├── Phase/                    # Phase 1–6 reports and roadmap (English + Korean)
├── plan/                     # MVP plan (Korean)
├── rag_mvp_sample_documents/ # Reviewed source PDFs and corpus guide
├── docs/evidence/            # Screenshots of the running app
├── .streamlit/               # Theme and secrets template
├── DEPLOYMENT.md             # Deployment guide (English + Korean)
├── .env.example              # Settings template
├── requirements.txt          # Runtime dependencies
└── requirements-dev.txt      # Test dependencies
```

Credentials, the local Chroma database, model downloads, private trace files, generated previews, and check results are excluded from Git.

## Current Status

| Phase | Status | Deliverable |
| --- | --- | --- |
| [1 — Foundation](Phase/Phase1_Foundation.md) | ✅ Done | Page-level extraction of 4 PDFs into 22 chunks with source metadata |
| [2 — Indexing and retrieval](Phase/Phase2_IndexingAndRetrieval.md) | ✅ Done | Local E5 embeddings, persistent Chroma index, reuse and explicit rebuild |
| [3 — Grounded answers](Phase/Phase3_GroundedAnswers.md) | ✅ Done | One Claude call per question, quote-validated citations, abstention |
| [4 — Streamlit interface](Phase/Phase4_StreamlitInterface.md) | ✅ Done (local) | Chat with sources, example questions, safe errors, per-session limit |
| [5 — Evaluation and deployment](Phase/Phase5_EvaluationAndDeployment.md) | 🔧 In progress | 10- and 60-question evaluations; [public demo](https://enterprise-rag-demo-project.streamlit.app/) deployed 2026-10-16; LangSmith trace verified against remote records for local execution. Human review and broader Cloud checks are deferred |
| [6 — Retrieval and answer quality](Phase/Phase6_RetrievalAndAnswerQuality.md) | ✅ Done (local); grading partly deferred | Opt-in page context (pages, k=5, 6,000 chars); answer prompt spells out required items, conditions, and timing; frozen 60-question paired evaluator with offline audit and review recovery |

- The code default is `chunks` with k=3. The owner reports that the live demo runs page mode (pages, k=5, 6,000 chars) after a reboot; this has not been independently verified.
- This revision includes the Phase 6 tracing fixes, frozen evaluator, validation diagnostics, final-page selection, and review recovery. The latest checks were local; Cloud behavior has not been reverified for these changes.

## Limitations

- **Small synthetic corpus.** 4 PDFs and 13 pages. Results do not show performance on real enterprise documents.
- **Page-mode answer accuracy is unknown.** AI grading of the frozen comparison is incomplete.
- **No human grading yet.** Correctness scores come from the same model that generated the answers.
- **No unseen test set.** All 60 expanded questions were inspected during development, so the final-check split is not a holdout.
- **Fixed corpus.** No document upload, OCR, table recognition, authentication, or document permissions.
- **Demo-scale serving.** Requests are serialized by a shared lock. The question limit is per session, not a provider-wide budget. Concurrent use has not been tested.
- **Cloud behavior only partly verified.** Tracing was verified for local execution, not for the deployed app. Restart, startup time, and memory use on Streamlit Community Cloud have not been checked.

## Roadmap

From the [development status and roadmap](Phase/DevelopmentStatusAndRoadmap.md):

Validation-rule logging and final-page selection are implemented and tested locally. The next step is to **prepare fresh independent questions**, with references and scoring frozen before evaluation. When the owner resumes API use, check actual diagnostic capture and answer quality under the new selector.

The refreshed recovery plan covers the same 87 saved old answers; completing those grades will not measure the new selector. The previous plan and all earlier results remain intact.

Deferred by the owner: the 87 failed AI reviews (resume with `eval.recover_reviews` once API access is funded) and the 34-entry human review. Optional later work: Cloud resource checks, CI, and SDK maintenance. Deferred or excluded: Phase 7 usability and concurrency testing.

## Documentation

| Document | Contents |
| --- | --- |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Cloud setup, secrets, page-mode activation, LangSmith verification (English + Korean) |
| [Development status and roadmap](Phase/DevelopmentStatusAndRoadmap.md) | Latest audit, quality findings, prioritized next work |
| [Phase reports](Phase/) | Design, implementation, and verification evidence for each phase (English + Korean) |
| [MVP plan](plan/enterprise_rag_assistant_streamlit_mvp_plan.md) | Requirements, architecture, acceptance criteria (Korean) |
| [Sample document guide](rag_mvp_sample_documents/README.md) | Corpus details and evidence-matching rules (Korean) |
| [60-question evaluation report](eval/results/phase5_v2_20261014/report.md) | k=3 vs k=5 comparison, failure analysis, review queue (Korean) |
| [Page-context report](eval/results/phase6_20261016/report.md) | Retrieval comparison and known-case checks (Korean) |
| [Frozen comparison report](eval/results/phase6_quality_20261016/report.md) | chunks/k=5 vs pages/k=5 on 60 questions, with full denominators (Korean) |

---
<p align="center">Made with AI-assisted development</p>
