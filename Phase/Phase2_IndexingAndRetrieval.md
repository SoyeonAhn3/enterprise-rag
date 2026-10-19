# Phase 2 — Indexing and Retrieval `✅ Completed`

> Build a reusable Chroma index and retrieve the top three chunks for a question.

**Updated**: 2026-10-14\
**Status**: ✅ Completed — real local model build/reuse and q01/q07/q08 retrieval passed; 108 automated tests passed.\
**Prerequisites**: [Phase 1](Phase1_Foundation.md) verification complete; download the local model once, then use its cache. No API key is required for Phase 2.\
**Technology**: Python 3.12, FastEmbed, ONNX Runtime, langchain-chroma, Chroma, pytest. Claude SDK prepared for Phase 3.

**Portfolio review — 2026-10-19:** This report preserves the implementation contract and measurements at this phase’s completion. The agreed portfolio scope is now complete; later retrieval options, answer/citation improvements, 488 passing tests, and the owner-reported Cloud setting are recorded in the [current roadmap](DevelopmentStatusAndRoadmap.md). No foundation or indexing change was needed for this documentation review.

## Overview

Extend the validated PDF pipeline with offline embeddings and persistent storage at `data/chroma_db/`. Query processing loads that index, embeds the question, and performs one top-three similarity search. Answer generation belongs to [Phase 3](Phase3_GroundedAnswers.md).

Phase 1 supplied 22 validated chunks. On 2026-10-14 the user selected **Claude for generation and local multilingual embeddings for retrieval**. The current model is `intfloat/multilingual-e5-small`, 384 dimensions, running on CPU through FastEmbed/ONNX. A usable index now exists at `data/chroma_db/`. [Anthropic does not offer its own embedding model](https://platform.claude.com/docs/en/build-with-claude/embeddings). The earlier OpenAI credit failures are retained below as historical checks and no longer block retrieval.

## Tasks & Verification

| Task | Work and completion criteria | Verification | Status |
| --- | --- | --- | --- |
| 2.1 | Load environment/local settings without exposing credentials; separate Claude from local embeddings | Configuration, local-model contracts, and Claude SDK HTTP/error tests | ✅ Passed |
| 2.2 | Persist all chunks in Chroma and activate a validated manifest | Real local E5 model and Chroma; exact record comparison | ✅ Passed |
| 2.3 | Reuse matching indexes; reject stale inputs; preserve the active index on failed rebuilds | Repeated builds, changed settings/documents, failed writes | ✅ Passed |
| 2.4 | Reload in a new process and return the original top three chunks without re-embedding documents | Real offline fresh-process retrieval with network/document embedding forbidden; call-count tests | ✅ Passed |
| 2.5 | Verify q01/q07/q08 with the real local model and document observed retrieval | Saved results and original-quote inspection; all required groups found | ✅ Passed |
| 2.6 | Record checks, limitations, commands, and synchronized README status | Bilingual report, reproducible commands, README synchronization | ✅ Recorded |

## Deliverables and completion criteria

| Deliverable | Completion criterion | Verification approach |
| --- | --- | --- |
| Embedding and index build | All prepared chunks are saved with their actual source metadata; only runtime PDFs enter the index | Build with the real corpus; compare stored IDs, metadata, and counts |
| Reusable index | A new process reloads the saved index without embedding the documents again | Restart the process and inspect calls and stored counts |
| Top-three retrieval | A question returns three actual indexed chunks, including text and page metadata | Inspect retrieval for q01, q07, and q08; retain all three results for later evaluation |
| Rebuild and error behavior | Repeated builds do not duplicate chunks; changed corpus/settings/model cannot silently use an incompatible or stale index | Rebuild/reload checks and missing-key/index/API error cases |

Implemented files:

- `config.py`, `.env.example`: shared environment/server-secret/local-file configuration, validated settings, and hidden key representation. Priority is environment → supplied server secrets → `.env` → defaults. Streamlit integration remains Phase 4 work.
- `embeddings.py`: local multilingual E5 through FastEmbed, explicit document/query prefixes, mean pooling and normalization, model/dimension validation, CPU inference, configurable cache and offline loading. Returned vectors must have the expected count/dimensions and finite, nonzero values. No embedding API is called.
- `llm.py`: official Anthropic SDK, configurable Claude model/output cap, a 30-second timeout, zero retries, sanitized errors, and rejection of incomplete/refused/empty text. `--check` calls the Models API without generation. Grounded RAG orchestration remains Phase 3 work.
- `index_store.py`: persistent Chroma storage, corpus/configuration fingerprints, exact text/metadata/ID validation, index reuse, and explicit rebuilds with an atomically replaced manifest.
- `ingest.py`: preserved API-free `--dry-run`; normal invocation builds/reuses the index, while `--rebuild` creates a new active collection.
- `rag.py`: `Retriever.retrieve(question)` and a CLI returning the question, all three retrieved chunks (`S1`–`S3`), original text/metadata, cosine distance, and retrieval latency. Answer generation is not implemented in this phase.
- `eval/check_retrieval.py`: reproducible q01/q07/q08 retrieval checks; only question text enters retrieval. Reference evidence is inspected afterwards. Full answer evaluation remains Phase 5 work.

## Initial verification before provider migration

Initially verified on **Windows / Python 3.12.10 / 2026-10-13**, with **81 passed in 17.87s** and successful dependency installation. Reverified on **2026-10-14**: **81 passed in 28.46s**, exit code 0; `pip check` reported no broken requirements. The dry run still reports **4 PDFs / 13 pages / 0 skipped pages / 22 chunks**. Original PDFs and evaluation content were not modified.

| Check | Observed result |
| --- | --- |
| Existing preprocessing/evidence checks | 35 tests passed; all 20 original evidence quotes still fit their declared pages and chunks |
| Configuration and SDK contract/errors | 17 tests passed using the actual SDK with mocked HTTP; credentials are not echoed and failures make one attempt |
| Persistent indexing and retrieval | 25 tests passed using real local Chroma with deterministic test embeddings |
| Smoke-check evidence assessment | 4 tests passed; alternative evidence uses OR, required groups use AND, and a page hit alone does not count as a quote hit |
| Repeated build | Active collection and 22 unique records reused; document embedding call count remains one |
| Fresh process | Three chunks returned with zero document-embedding calls and one question-embedding call |
| Stale/corrupt state | Changed PDFs/model/dimensions/chunk settings, missing manifest/collection, deleted chunks, and altered metadata rejected |
| Rebuild and recovery | Removing one PDF activates only the current 16 chunks; failed embedding/manifest writes preserve the previous active collection; a failed first build recovers with `--rebuild` |
| Input snapshots | Changed PDFs between preparation/build or during embedding cannot activate mislabeled chunks |
| Secret/generated files | `.env`, Chroma files, and generated previews/check results are ignored; `.env.example` remains shareable |
| Real OpenAI embedding build | Failed: HTTP 429; diagnostic response code `credit_balance_exhausted`, type `insufficient_quota` |
| Real retrieval check | Correctly refused the incomplete index with exit code 1 and a `--rebuild` instruction; no successful retrieval result file was produced |

Test embeddings are isolated to temporary test directories and dependency injection. They establish persistence, integrity, and call behavior; they do **not** establish semantic retrieval quality. No test vectors were installed as the application index.

| Real-provider question | Required evidence | Current result |
| --- | --- | --- |
| q01 | Approval authority on `02_approval_budget.pdf`, page 1 | Not measured; index build blocked |
| q07 | Approval authority and IT security review | Not measured; index build blocked |
| q08 | Approval authority and legal review | Not measured; index build blocked |

The first provider failure was reported as a generic rate/usage error. A safe diagnostic inspected only the status/code/type and confirmed exhausted credits. Added a specific credit/quota error message and mocked regression cases. The [OpenAI error guide](https://developers.openai.com/api/docs/guides/error-codes) identifies `credit_balance_exhausted` as depleted organization credits; repeated retries do not resolve that condition. Credentials, organization identifiers, and raw provider responses are excluded from this report.

### 2026-10-14 retry before migration

Retried `ingest.py --rebuild` using the then-configured local `.env` OpenAI key. It exited with code 1 and the sanitized message `OpenAI API credit balance is exhausted. Check API billing before retrying.` The subsequent `python -m eval.check_retrieval` also exited with code 1. Neither the active manifest nor retrieval report existed at that point; this failure was resolved by the local-model migration below.

The 81-test suite, dependency check, and dry run passed again. Task 2.5 remained pending until the user requested the Claude/local-embedding configuration.

### Claude and local embedding migration — completed 2026-10-14

Removed `openai`/`langchain-openai` from the runtime requirements and virtual environment. Migrated `.env` and `.env.example` to `ANTHROPIC_*` and provider-independent `EMBEDDING_*` settings, preserving unrelated local settings and never reusing an OpenAI key for Anthropic. The initially empty Claude key was subsequently configured locally without being displayed. `llm.py --check` successfully verified `claude-sonnet-5-5` through the live Models API, and one short Messages API call returned `연결 확인`. This verifies connectivity and text generation, not grounded RAG answer quality. Error behavior remains covered by mocked HTTP tests.

The [E5 model](https://huggingface.co/intfloat/multilingual-e5-small) uses `passage: ` for documents and `query: ` for questions, mean pooling, and normalized 384-dimensional vectors. It is registered using [FastEmbed's custom-model interface](https://github.com/qdrant/fastembed#-dense-text-embeddings). The actual corpus's longest input is 411 tokens including the prefix, below the model's 512-token limit. Model cache size is 487,360,797 bytes; the current local index is approximately 0.71 MB. Both remain Git-ignored. These Windows measurements do not establish Cloud resource requirements.

Verification: **108 passed in 12.75s**, exit code 0; `pip check` found no broken requirements. The real model built all 22 records and a second ingestion reused the same collection. A new process loaded the cached model and completed the smoke check with socket networking disabled and document-embedding calls set to raise errors. All three original chunks per question were saved to `data/retrieval_smoke.json` and inspected.

After the user confirmed OneDrive deletions, rechecked the environment: **108 passed in 13.59s**, Python 3.12.10 runs, `pip check` reports no broken requirements, and the active index/model cache remain usable. The retrieval CLI also returned three chunks when launched from outside the project directory. No further package removal or installation was needed for these checks. Credentials, model cache, and generated index/retrieval files remain Git-ignored.

| Question | Retrieved sources in rank order | Required quote groups | Retrieval latency |
| --- | --- | --- | ---: |
| q01 | Approval p1, approval p3, approval p1 | Approval threshold: S3 | 12.15 ms |
| q07 | Approval p1, contracts p1, security p1 | Approval: S1; security review: S3 | 11.83 ms |
| q08 | Contracts p1, approval p3, approval p1 | Legal review: S1; approval: S2 | 12.51 ms |

All three questions have complete page and quote coverage; q07/q08 each include both required groups. q01's first result overlaps the right page but the needed threshold is in S3, so retaining all top-three chunks matters. These timings cover query embedding plus search after loading; they exclude model startup and answer generation. This is not the full Phase 5 retrieval/answer evaluation.

## Reproduce acceptance

Run from the project root in PowerShell. Copy `.env.example` only if `.env` is missing. No API key is needed for indexing/retrieval. Leave `EMBEDDING_LOCAL_FILES_ONLY=false` for the first model download; set it to `true` after caching for offline use. Set `ANTHROPIC_API_KEY` locally only when using Claude.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q

# Build with local embeddings; also required when migrating an old index.
.\.venv\Scripts\python.exe -X utf8 ingest.py --rebuild

# Confirm that unchanged input reuses the saved index.
.\.venv\Scripts\python.exe -X utf8 ingest.py

# Each command runs in a new process and loads the persistent index.
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
.\.venv\Scripts\python.exe -X utf8 -m eval.check_retrieval
```

Normal ingestion is sufficient for a fresh index. `--rebuild` is required when PDFs, embedding provider/model/dimensions, adapter behavior, or chunk settings change, or after an incomplete initial build. A matching index reuses the manifest/collection without loading a model or embedding documents. A successful smoke run writes `data/retrieval_smoke.json` with all three chunks, signature, timing, page matches, and whitespace-only quote matches. Exit code 0 means the run was recorded, not that every group was found. Whole-application latency, answer correctness, and abstention are not measured here. To check Claude access separately without generation, run `.\.venv\Scripts\python.exe -X utf8 llm.py --check` after entering its key.

Pinned runtime dependencies: PyMuPDF **1.28.2**, langchain-core **1.6.10**, langchain-text-splitters **1.1.3**, langchain-chroma **1.1.0**, chromadb **1.5.9**, FastEmbed **0.9.0**, ONNX Runtime **1.31.0**, Anthropic **1.13.0**, python-dotenv **1.2.4**. Development dependencies add pytest **9.1.1** and httpx2 **2.13.1** for the Claude SDK transport tests. Cloud compatibility remains unverified.

## Decisions and dependencies

- Document and query embeddings use the same configured model/dimensions. The manifest records PDF hashes, chunk size/overlap, extraction versions, and cosine distance. Load rejects incompatible signatures before querying.
- On load, verify PDF hashes and all stored text/metadata/IDs once. This reads the PDF bytes for hashing but does not extract or re-embed documents. A retained `Retriever` performs only question embedding and one top-three search per valid question. Future Streamlit caching belongs to Phase 4.
- The manifest selects one validated collection. Explicit rebuilds retain older/incomplete collections in the local database so a failed build does not destroy the active index. Those collections are not queried, but repeated rebuilds can grow disk usage; cleanup is not automated.
- This is an offline, single-writer workflow. Do not rebuild while an application instance holds a cached retriever; restart it after replacing the corpus/index. Concurrent writers and online index switching are outside this MVP.
- Only direct runtime PDFs enter the index. Evaluation questions, reference answers, and annotations are never ingested. Retrieval checks pass only the selected question to the retriever.
- A valid question contains 1–500 characters after trimming. Similarity distance is not confidence or proof of answerability. Retrieval preserves all three results for later coverage assessment; Phase 3 must decide whether the available text supports an answer.
- The generated index and model cache remain Git-ignored pending a deployment decision. The model is downloaded once; documents and questions are embedded locally. No UI, grounded answer generation, LangSmith trace, or Cloud deployment is claimed complete.

## Handoff status

**Phase 2 is complete with the user-selected local embedding model.** The real 22-chunk index and inspected q01/q07/q08 evidence are ready for [Phase 3](Phase3_GroundedAnswers.md). The Claude adapter and live API access are verified; grounded generation/source validation remain required in that phase. A separate dev-log entry was skipped because the `dev-log` skill is unavailable; this bilingual report and change log carry the development record.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the scope, prerequisites, and completion criteria; detailed implementation remains pending. |
| 2026-10-13 | Implemented configuration, persistent indexing, retrieval, and smoke-check tooling; 81 tests passed. Real API validation stopped on exhausted credits; recorded recovery commands and kept Phase 2 in progress. |
| 2026-10-14 | Resumed acceptance: 81 tests passed in 28.46s; dependency check and 22-chunk dry run passed. Real rebuild still failed on exhausted credits; retrieval refused the missing manifest. Updated this report and both READMEs; Task 2.5 remains pending. |
| 2026-10-14 | Replaced OpenAI with the requested Claude backend and local multilingual E5 embeddings. Migrated environment/configuration, dependencies, and compatibility checks; 108 tests passed. Real build/reuse and offline fresh-process q01/q07/q08 quote coverage passed; completed Phase 2. Live Claude access awaits a key. |
| 2026-10-14 | After OneDrive deletion confirmation, reverified the environment: 108 tests passed in 13.59s, dependencies and cached retrieval intact. The configured Claude key passed live Models and Messages API checks. Updated current status and Phase 3 handoff. |
| 2026-10-19 | Reviewed against the completed portfolio; linked current status while retaining original phase measurements. Documentation only; separate dev-log unavailable. |

---

# Phase 2 — 벡터 인덱싱 및 검색 `✅ 완료`

> 재사용 가능한 Chroma 인덱스를 만들고 질문에 관련된 청크 상위 3개를 검색한다.

**갱신일**: 2026-10-14\
**상태**: ✅ 완료 — 실제 로컬 모델 생성·재사용 및 q01·q07·q08 검색 검증 통과, 자동 테스트 108개 통과.\
**선행 조건**: [Phase 1](Phase1_Foundation.md) 검증 완료, 로컬 모델 최초 다운로드 후 캐시 사용. Phase 2에는 API 키가 필요 없다.\
**기술 구성**: Python 3.12, FastEmbed, ONNX Runtime, langchain-chroma, Chroma, pytest. Phase 3용 Claude SDK 준비.

**포트폴리오 점검 — 2026-10-19:** 이 문서의 구현 계약과 측정값은 해당 Phase 완료 당시 기록으로 보존한다. 합의한 포트폴리오 범위는 완료했으며, 이후 검색 옵션·답변 및 인용 개선·테스트 488개 통과·사용자의 Cloud 설정 완료 보고는 [최신 로드맵](DevelopmentStatusAndRoadmap.md)에 정리했다. 이번 문서 점검에서 기반·인덱싱 코드를 변경하지 않았다.

## 개요

검증한 PDF 파이프라인에 오프라인 임베딩을 연결하고 `data/chroma_db/`에 인덱스를 저장한다. 질문 처리 시에는 저장한 인덱스를 불러와 질문을 임베딩하고 상위 3개 유사도 검색을 한 번 수행한다. 답변 생성은 [Phase 3](Phase3_GroundedAnswers.md)에서 구현한다.

Phase 1에서 검증한 청크 22개를 사용한다. 2026-10-14 사용자가 **답변 생성은 Claude, 검색은 로컬 다국어 임베딩**으로 선택했다. 현재 모델은 `intfloat/multilingual-e5-small`, 384차원이며 FastEmbed/ONNX를 통해 CPU에서 실행한다. `data/chroma_db/`에 실제 사용 가능한 인덱스를 생성했다. [Anthropic은 자체 임베딩 모델을 제공하지 않는다](https://platform.claude.com/docs/en/build-with-claude/embeddings). 기존 OpenAI 크레딧 오류는 아래 과거 검증 기록에 보존하며 현재 검색을 막는 조건이 아니다.

## Task 및 검증

| Task | 작업 및 완료 기준 | 검증 방법 | 상태 |
| --- | --- | --- | --- |
| 2.1 | 인증 정보 노출 없이 설정을 읽고 Claude와 로컬 임베딩을 분리함 | 설정·로컬 모델 계약·Claude SDK HTTP 및 오류 테스트 | ✅ 통과 |
| 2.2 | 모든 청크를 Chroma에 저장하고 검증한 매니페스트를 활성화함 | 실제 로컬 E5 모델 및 Chroma, 레코드 전체 대조 | ✅ 통과 |
| 2.3 | 같은 인덱스를 재사용하고 입력 변경을 감지하며 재생성 실패 시 기존 활성 인덱스를 보존함 | 반복 생성·설정 및 문서 변경·쓰기 실패 테스트 | ✅ 통과 |
| 2.4 | 새 프로세스에서 재로딩하고 문서 재임베딩 없이 원래 검색된 상위 3개를 반환함 | 네트워크·문서 임베딩을 금지한 실제 별도 프로세스 검색 및 호출 횟수 검사 | ✅ 통과 |
| 2.5 | 실제 로컬 모델로 q01·q07·q08을 확인하고 검색 결과를 기록함 | 저장 결과 및 원문 발췌 검토, 필수 그룹 모두 확보 | ✅ 통과 |
| 2.6 | 검사 결과·한계·명령·README 상태를 동기화함 | 영문·국문 보고서, 재현 명령, README 동기화 | ✅ 기록 완료 |

## 산출물 및 완료 기준

| 산출물 | 완료 기준 | 검증 방향 |
| --- | --- | --- |
| 임베딩·인덱스 생성 | 준비한 모든 청크를 실제 출처 메타데이터와 함께 저장하고 실행용 PDF만 색인함 | 실제 문서로 생성한 뒤 저장 ID·메타데이터·개수 비교 |
| 인덱스 재사용 | 새 프로세스에서 기존 인덱스를 불러오며 문서 임베딩을 반복하지 않음 | 프로세스 재시작 후 호출 및 저장 개수 확인 |
| 상위 3개 검색 | 질문마다 실제 저장 청크 3개와 본문·페이지 메타데이터를 반환함 | q01·q07·q08 검색 결과 확인, 후속 평가를 위해 3개 결과 모두 보존 |
| 재생성·오류 처리 | 반복 생성 시 중복이 없고 문서·설정·모델 변경 시 오래되거나 호환되지 않는 인덱스를 조용히 사용하지 않음 | 재생성·재로딩 검사, 키·인덱스 누락 및 API 오류 확인 |

구현한 파일:

- `config.py`, `.env.example`: 환경변수·서버 시크릿·로컬 파일 공통 설정, 값 검증, 키의 문자열 표현 제외. 우선순위는 환경변수 → 전달된 서버 시크릿 → `.env` → 기본값이다. Streamlit 연결은 Phase 4 대상이다.
- `embeddings.py`: FastEmbed 기반 로컬 다국어 E5. 문서·질문 접두어, 평균 풀링·정규화, 모델·차원 검증, CPU 추론, 캐시 경로·오프라인 로딩 설정을 적용한다. 벡터의 개수·차원·유한한 값·0벡터 여부를 검사하며 임베딩 API는 호출하지 않는다.
- `llm.py`: 공식 Anthropic SDK, Claude 모델·출력 한도 설정, 제한 시간 30초, 재시도 0회, 안전한 오류 안내, 미완성·거부·빈 응답 거절. `--check`는 답변 생성 없이 Models API로 연결을 검사한다. 근거 기반 RAG 연결은 Phase 3 대상이다.
- `index_store.py`: Chroma 영구 저장, 문서·설정 지문, 본문·메타데이터·ID 전체 검증, 인덱스 재사용, 매니페스트를 원자적으로 교체하는 명시적 재생성.
- `ingest.py`: API 없는 `--dry-run` 유지. 일반 실행은 인덱스를 생성·재사용하고 `--rebuild`는 새 활성 컬렉션을 만든다.
- `rag.py`: `Retriever.retrieve(question)`과 CLI. 질문, 검색 청크 3개 전체(`S1`~`S3`), 원문·메타데이터, 코사인 거리, 검색 시간을 반환한다. 이 단계에는 답변 생성이 없다.
- `eval/check_retrieval.py`: q01·q07·q08 검색을 재현하는 검증 도구. 검색에는 질문 문자열만 전달하고 이후 참고 근거와 비교한다. 전체 답변 평가는 Phase 5 대상이다.

## 제공업체 전환 전 초기 검증 기록

최초 **2026-10-13 / Windows / Python 3.12.10**에서 **81 passed in 17.87s**와 의존성 설치 성공을 확인했다. **2026-10-14** 재검증 결과는 종료 코드 0, **81 passed in 28.46s**이며 `pip check`에서 충돌이 없었다. Dry run은 **PDF 4개 / 13페이지 / 제외 0페이지 / 청크 22개**를 유지한다. 원본 PDF와 평가 내용은 수정하지 않았다.

| 검사 | 실제 결과 |
| --- | --- |
| 기존 전처리·근거 검사 | 35개 통과. 원문 근거 20개 모두 지정 페이지와 청크에서 보존됨 |
| 설정 및 SDK 계약·오류 | 실제 SDK와 HTTP 모의 응답으로 17개 통과. 인증 정보 미출력, 실패 시 요청 1회 |
| 영구 인덱싱·검색 | 결정적 테스트 임베딩과 실제 로컬 Chroma로 25개 통과 |
| 검색 검증 도구의 근거 판정 | 4개 통과. 대체 근거 OR·필수 그룹 AND, 페이지 일치만으로 발췌 일치 처리하지 않음 |
| 반복 생성 | 활성 컬렉션과 고유 레코드 22개 재사용. 문서 임베딩 호출 수 1회 유지 |
| 새 프로세스 | 문서 임베딩 0회·질문 임베딩 1회로 청크 3개 반환 |
| 오래되거나 손상된 상태 | PDF·모델·차원·청크 설정 변경, 매니페스트·컬렉션 누락, 청크 삭제, 메타데이터 변경을 거부 |
| 재생성·복구 | PDF 하나 삭제 후 현재 청크 16개만 활성화. 임베딩·매니페스트 쓰기 실패 시 기존 활성 컬렉션 보존. 첫 생성 실패 후 `--rebuild` 복구 |
| 입력 스냅샷 | 준비·생성 사이 또는 임베딩 중 PDF가 바뀌면 잘못된 문서 버전의 청크를 활성화하지 않음 |
| 시크릿·생성 파일 | `.env`, Chroma, 미리보기·검색 결과는 Git 제외. `.env.example`은 공유 가능 |
| 실제 OpenAI 임베딩 생성 | 실패: HTTP 429. 진단 응답 코드 `credit_balance_exhausted`, 유형 `insufficient_quota` |
| 실제 검색 검사 | 미완성 인덱스를 종료 코드 1과 `--rebuild` 안내로 정상 거부. 성공한 검색 결과 파일은 생성하지 않음 |

테스트 임베딩은 임시 테스트 폴더와 의존성 주입으로만 사용했다. 저장·정합성·호출 동작을 검증하며 의미 기반 검색 품질을 입증하지는 않는다. 실행용 인덱스에 테스트 벡터를 설치하지 않았다.

| 실제 제공업체 질문 | 필요한 근거 | 현재 결과 |
| --- | --- | --- |
| q01 | `02_approval_budget.pdf` 1쪽 결재권자 | 인덱스 생성 차단으로 미측정 |
| q07 | 결재권자와 IT 보안검토 | 인덱스 생성 차단으로 미측정 |
| q08 | 결재권자와 법무 검토 | 인덱스 생성 차단으로 미측정 |

첫 제공업체 실패는 일반적인 호출·사용 한도 오류로 표시됐다. 상태·코드·유형만 확인하는 안전한 진단으로 크레딧 소진을 확인했다. 크레딧·할당량별 오류 문구와 HTTP 모의 회귀 검사를 추가했다. [OpenAI 오류 안내](https://developers.openai.com/api/docs/guides/error-codes)에 따르면 `credit_balance_exhausted`는 조직의 크레딧 소진을 뜻하며, 반복 재시도로 해결되지 않는다. 이 보고서에는 인증 정보, 조직 식별자, 제공업체 응답 원문을 포함하지 않는다.

### 2026-10-14 전환 전 재시도

당시 로컬 `.env`의 OpenAI 키로 `ingest.py --rebuild`를 재실행했다. 종료 코드 1과 안전한 오류 문구 `OpenAI API credit balance is exhausted. Check API billing before retrying.`를 반환했다. 이어서 실행한 `python -m eval.check_retrieval`도 종료 코드 1을 반환했다. 당시에는 활성 매니페스트와 검색 보고서가 없었으며, 아래 로컬 모델 전환으로 이 실패를 해소했다.

테스트 81개, 의존성 검사, Dry run은 다시 통과했다. 사용자가 Claude·로컬 임베딩 구성을 요청하기 전까지 Task 2.5는 대기 상태였다.

### Claude·로컬 임베딩 전환 — 2026-10-14 완료

실행 의존성과 가상환경에서 `openai`·`langchain-openai`를 제거했다. `.env`와 `.env.example`을 `ANTHROPIC_*` 및 제공업체와 독립적인 `EMBEDDING_*` 설정으로 전환했다. 관련 없는 기존 설정은 유지했고 OpenAI 키를 Anthropic 키로 재사용하지 않았다. 처음 비어 있던 Claude 키는 이후 로컬에 설정됐으며 값을 표시하지 않았다. `llm.py --check`로 실제 Models API에서 `claude-sonnet-5-5` 접근을 확인했고 짧은 Messages API 호출 1회에서 `연결 확인` 응답을 받았다. 연결과 텍스트 생성을 확인한 것이며 근거 기반 RAG 답변 품질 검증은 아니다. 오류 동작은 HTTP 모의 응답 테스트로 확인했다.

[E5 모델](https://huggingface.co/intfloat/multilingual-e5-small)에 문서 `passage: `·질문 `query: ` 접두어, 평균 풀링 및 384차원 정규화를 적용한다. [FastEmbed 사용자 모델 등록 방식](https://github.com/qdrant/fastembed#-dense-text-embeddings)을 사용했다. 실제 문서의 최대 입력은 접두어를 포함해 411토큰으로 모델 한도 512토큰 이내다. 모델 캐시는 487,360,797바이트, 현재 로컬 인덱스는 약 0.71 MB이며 모두 Git에서 제외한다. Windows 측정값이므로 Cloud 자원 요구량을 입증하지는 않는다.

검증 결과 **108 passed in 12.75s**, 종료 코드 0이며 `pip check`에서 충돌이 없었다. 실제 모델로 22개 레코드를 생성했고 두 번째 인덱싱은 같은 컬렉션을 재사용했다. 새 프로세스에서는 소켓 네트워크를 차단하고 문서 임베딩 호출 시 오류가 발생하도록 설정한 뒤 캐시 모델로 검색 검증을 완료했다. 질문별 원래 청크 3개 전체를 `data/retrieval_smoke.json`에 저장하고 원문을 확인했다.

사용자가 OneDrive 삭제를 확인한 뒤 환경을 재검사했다. **108 passed in 13.59s**이며 Python 3.12.10 실행, `pip check` 의존성 충돌 없음, 활성 인덱스·모델 캐시의 정상 사용을 확인했다. 프로젝트 외부 경로에서 실행한 검색 CLI도 청크 3개를 반환했다. 이 검사에는 추가 패키지 제거·설치가 필요하지 않았다. 인증 정보·모델 캐시·생성 인덱스·검색 결과는 Git 제외 상태를 유지한다.

| 질문 | 순위별 검색 출처 | 필수 근거 발췌 그룹 | 검색 시간 |
| --- | --- | --- | ---: |
| q01 | 결재 규정 1쪽, 결재 규정 3쪽, 결재 규정 1쪽 | 결재 금액 기준: S3 | 12.15 ms |
| q07 | 결재 규정 1쪽, 계약 지침 1쪽, 보안 지침 1쪽 | 결재권자: S1, 보안검토: S3 | 11.83 ms |
| q08 | 계약 지침 1쪽, 결재 규정 3쪽, 결재 규정 1쪽 | 법무 검토: S1, 결재권자: S2 | 12.51 ms |

세 문항 모두 필수 페이지·발췌를 확보했고 q07·q08은 각각 필요한 두 그룹을 모두 포함한다. q01의 첫 결과는 같은 페이지지만 필요한 금액 기준은 S3에 있으므로 상위 3개 전체를 유지해야 한다. 시간은 모델 로딩 후 질문 임베딩과 검색만 포함하며 모델 초기화·답변 생성은 제외한다. Phase 5 전체 검색·답변 평가는 아니다.

## 인수 검증 재현

프로젝트 루트의 PowerShell에서 실행한다. `.env`가 없을 때만 `.env.example`을 복사한다. 인덱싱·검색에는 API 키가 필요 없다. 모델 최초 다운로드 시 `EMBEDDING_LOCAL_FILES_ONLY=false`를 유지하고 캐시 생성 후 `true`로 바꾸면 오프라인으로 로딩한다. Claude 사용 시에만 로컬 `ANTHROPIC_API_KEY`를 입력한다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q

# 로컬 임베딩 생성. 기존 인덱스에서 전환할 때도 필요
.\.venv\Scripts\python.exe -X utf8 ingest.py --rebuild

# 같은 입력이면 저장한 인덱스를 재사용하는지 확인
.\.venv\Scripts\python.exe -X utf8 ingest.py

# 각각 새 프로세스에서 영구 인덱스를 불러옴
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
.\.venv\Scripts\python.exe -X utf8 -m eval.check_retrieval
```

처음 만드는 정상 인덱스에는 일반 실행으로 충분하다. PDF·임베딩 제공업체·모델·차원·어댑터 동작·청크 설정 변경 또는 불완전한 최초 생성 이후에는 `--rebuild`가 필요하다. 일치하는 인덱스는 모델 로딩·문서 임베딩 없이 재사용한다. 검색 검사 성공 시 `data/retrieval_smoke.json`에 청크 3개, 지문, 시간, 페이지 일치, 공백만 무시한 발췌 일치를 저장한다. 종료 코드 0은 결과 저장을 뜻하며 모든 그룹 확보를 뜻하지 않는다. 전체 앱 응답 시간·답변 정확도·답변 보류는 이 단계에서 측정하지 않는다. Claude는 키 입력 후 `.\.venv\Scripts\python.exe -X utf8 llm.py --check`로 답변 생성 없이 연결을 별도 확인한다.

고정한 실행 의존성: PyMuPDF **1.28.2**, langchain-core **1.6.10**, langchain-text-splitters **1.1.3**, langchain-chroma **1.1.0**, chromadb **1.5.9**, FastEmbed **0.9.0**, ONNX Runtime **1.31.0**, Anthropic **1.13.0**, python-dotenv **1.2.4**. 개발 의존성은 pytest **9.1.1**과 Claude SDK HTTP 검사에 사용하는 httpx2 **2.13.1**을 추가한다. Cloud 호환성은 미검증이다.

## 결정 사항 및 의존성

- 문서와 질문은 같은 모델·차원을 사용한다. 매니페스트에 PDF 해시, 청크 크기·중복, 추출 버전, 코사인 거리를 기록하고, 호환되지 않는 지문은 검색 전에 거부한다.
- 로딩 때 PDF 해시와 저장한 본문·메타데이터·ID를 한 번 검사한다. 해시 계산을 위해 PDF 바이트를 읽지만 텍스트 추출·문서 재임베딩은 하지 않는다. 유지된 `Retriever`는 유효 질문마다 질문 임베딩과 상위 3개 검색만 한 번 수행한다. Streamlit 캐시는 Phase 4 대상이다.
- 매니페스트가 검증된 컬렉션 하나를 선택한다. 재생성 실패로 활성 인덱스가 사라지지 않도록 이전·미완성 컬렉션은 로컬 DB에 보존한다. 해당 컬렉션은 검색하지 않지만 반복 재생성 시 디스크 사용량이 늘 수 있으며 자동 정리는 구현하지 않았다.
- 오프라인 단일 작성자 작업 흐름이다. 앱이 캐시한 검색기를 사용하는 동안 재생성하지 않으며 문서·인덱스를 교체한 뒤 앱을 다시 시작한다. 동시 작성과 온라인 인덱스 전환은 MVP 범위 밖이다.
- 실행용 폴더 바로 아래의 PDF만 색인한다. 평가 질문·참고 정답·주석을 색인하지 않으며 검색 검증에서는 선택한 질문만 검색기에 전달한다.
- 유효 질문은 앞뒤 공백 제거 후 1~500자다. 유사도 거리는 신뢰도나 답변 가능성의 증명이 아니다. 후속 Coverage 평가를 위해 결과 3개를 모두 보존하며, 실제 본문이 답변을 뒷받침하는지는 Phase 3에서 판단한다.
- 배포 결정 전까지 인덱스와 모델 캐시는 Git에서 제외한다. 모델은 한 번 다운로드하고 문서·질문 임베딩은 로컬에서 수행한다. UI·근거 기반 답변 생성·LangSmith 추적·Cloud 배포를 완료로 표시하지 않는다.

## 다음 단계 전달 상태

**사용자가 선택한 로컬 임베딩 모델로 Phase 2를 완료했다.** 실제 청크 22개 인덱스와 검토한 q01·q07·q08 근거를 [Phase 3](Phase3_GroundedAnswers.md)에 전달한다. Claude 어댑터와 실제 API 접근은 검증했으며 해당 단계에서는 근거 기반 생성·출처 검증이 필요하다. `dev-log` 스킬을 사용할 수 없어 별도 개발 로그는 생략했고, 이 영문·국문 보고서와 변경 이력으로 개발 내용을 기록했다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 범위·선행 조건·완료 기준 신규 작성. 상세 구현은 후속 진행 대상으로 기록함. |
| 2026-10-13 | 설정·영구 인덱싱·검색·검색 검증 도구 구현, 테스트 81개 통과. 실제 API 검증은 크레딧 소진으로 중단되어 복구 명령을 기록하고 Phase 2 진행 중 상태를 유지함. |
| 2026-10-14 | 인수 검증 재개: 81개 테스트 28.46초 통과, 의존성 검사 및 청크 22개 Dry run 통과. 실제 재생성은 크레딧 소진으로 다시 실패했고 검색은 매니페스트 누락을 거부함. 보고서·영문·국문 README를 갱신하고 Task 2.5 대기를 유지함. |
| 2026-10-14 | 요청한 Claude 호출 모듈과 로컬 다국어 E5로 OpenAI를 교체함. 환경 파일·설정·의존성·호환성 검사를 변경하고 테스트 108개 통과. 실제 생성·재사용·오프라인 새 프로세스 q01·q07·q08 발췌 확보를 검증해 Phase 2 완료. 실제 Claude 연결은 키 입력 대기. |
| 2026-10-14 | OneDrive 삭제 확인 후 환경 재검증: 108개 테스트 13.59초 통과, 의존성·캐시 검색 정상. 설정된 Claude 키로 실제 Models·Messages API 검증 통과. 현재 상태 및 Phase 3 전달 사항 갱신. |
| 2026-10-19 | 완료한 포트폴리오 기준으로 점검하고 최신 상태를 연결했다. 원래 Phase 측정값은 보존. 문서만 변경했으며 별도 dev-log 미설치로 여기에 기록. |
