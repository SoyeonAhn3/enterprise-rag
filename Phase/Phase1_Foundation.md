# Phase 1 — Foundation `✅ Completed`

> Prepare the local environment and verify PDF extraction, page metadata, and chunking before using an embedding API.

**Completed**: 2026-10-13\
**Status**: ✅ Completed — all five tasks and required local checks passed.\
**Prerequisites**: Reviewed MVP plan, four sample PDFs, and ten evaluation questions.\
**Technology**: Python 3.12, PyMuPDF, langchain-text-splitters, pytest.

## Overview

This phase produces a reproducible, offline input pipeline for the fixed demonstration corpus. Each chunk must retain its actual filename and physical page number. Evaluation questions and answers remain outside ingestion.

The overall sequence is **Foundation → Indexing and retrieval → Grounded answers → Streamlit interface → Evaluation, tracing, and deployment**. This document records the detailed Phase 1 tasks and results; subsequent phases will be refined before their implementation starts. The [MVP plan](../plan/enterprise_rag_assistant_streamlit_mvp_plan.md) remains the requirements baseline.

## Deliverables and current implementation

| Deliverable | Current evidence | Status |
| --- | --- | --- |
| Local environment | `.python-version`, `requirements.txt`, `requirements-dev.txt`; Python 3.12.10 environment, installation from the manifest, and `pip check` | ✅ Verified locally |
| Runtime corpus and evaluation data | Four PDFs in `documents/`; ten questions in `eval/questions.json`; all five files match the reviewed originals | ✅ Verified |
| Shared settings | `config.py`: project-relative paths, 800-character chunks, 120-character overlap setting | ✅ Verified, including execution outside the project directory |
| Offline ingestion | `ingest.py`: `extract_pages`, `split_pages`, `prepare_corpus`, `PreparedCorpus`, and a `--dry-run` CLI | ✅ Preview generated and checked |
| Ingestion tests | `tests/test_ingest.py`: actual corpus, evidence quotes, metadata, IDs, invalid inputs, CLI, and offline operation | ✅ 35 tests passed |

No Chroma index, embedding requests, generated answers, or RAG evaluation results were produced during Phase 1. Later implementation and provider checks are recorded in [Phase 2](Phase2_IndexingAndRetrieval.md).

## Tasks & Verification

| Task | Work | Acceptance criteria | Verification | Status |
| --- | --- | --- | --- | --- |
| 1.1 | Confirm the Python environment and installed dependency versions | The documented environment installs without dependency conflicts | `python --version`, `python -m pip check`, and the installation procedure below | ✅ Passed |
| 1.2 | Verify runtime copies and isolate the evaluation dataset | The four runtime PDFs and evaluation JSON match the reviewed sources; ingestion reads only direct PDF children | Compare file hashes; run corpus and input-isolation tests | ✅ Passed |
| 1.3 | Validate extraction and physical page numbers | All 13 sample pages yield text; skipped blank pages do not renumber later pages | Dry run, actual-corpus tests, and the blank-page fixture | ✅ Passed |
| 1.4 | Validate page-scoped chunks and stable IDs | Nonempty chunks respect the size limit, remain on one source page, and keep reproducible `source_file`, `page`, and `chunk_id` metadata | Inspect the preview and run source/ID tests | ✅ Passed |
| 1.5 | Verify input errors and command-line behavior | Missing, empty, corrupt, password-protected, or entirely textless input fails clearly; the CLI works outside the project directory | Run failure fixtures and CLI tests; confirm nonzero exit codes for invalid input | ✅ Passed |

**Results**: Verified on Windows with Python 3.12.10 on 2026-10-13. Installation from `requirements-dev.txt` succeeded; `pip check` reported no broken requirements. The final pytest run reported **35 passed in 2.75s** with exit code 0. The dry run also exited successfully and produced a valid UTF-8 JSON preview matching the in-memory corpus. All required local Phase 1 checks are complete; no additional project-specific user acceptance gate is defined.

## Verification Report

| PDF | Physical pages | Extracted text pages | Chunks |
| --- | ---: | ---: | ---: |
| `01_purchase_process.pdf` | 3 | 3 | 6 |
| `02_approval_budget.pdf` | 3 | 3 | 4 |
| `03_it_security.pdf` | 3 | 3 | 6 |
| `04_contract_settlement.pdf` | 4 | 4 | 6 |
| **Total** | **13** | **13** | **22** |

- **Integrity:** all four PDFs and the evaluation JSON match the reviewed originals. The real corpus has zero skipped pages. All 22 chunk IDs are unique and repeatable, and each chunk retains its actual source page. Chunk lengths range from **149 to 797 characters**.
- **Evidence preservation:** all **20 reference quotes** across **11 evidence groups** match their declared pages after ignoring layout whitespace. A separate check confirmed that each full quote also occurs in at least one of the generated chunks for that page. This is corpus coverage, not measured retrieval Hit@3 or answer correctness.
- **Visual/text review:** compared the approval table on `02_approval_budget.pdf` page 1, the corrected FAQ on `01_purchase_process.pdf` page 3, and security requirements on `03_it_security.pdf` page 1 with their rendered PDF pages. Approval amounts/authorities, the FAQ's 300만원 condition, and security-review wording remain in the correct reading order.
- **Failure cases:** missing/empty input directories, corrupt/zero-byte/password-protected/textless PDFs, a valid PDF mixed with a corrupt file, invalid chunk settings, and an unwritable preview destination behave as expected. CLI failures return a nonzero exit code and preserve the existing preview in the tested pre-write failure cases.
- **Isolation:** non-PDF files and nested evaluation PDFs are excluded. A dry run succeeded with API credentials removed and socket connection/DNS entrypoints blocked by the test. The CLI also succeeded from outside the project directory.
- **Artifact:** `data/chunks_preview.json` was generated locally (31,633 bytes) and is ignored by Git. Git ignore checks also covered the virtual environment and secret-file paths.

### Failure found and corrected

The first run had **24 passed and 2 failed**: q04/q07 quote checks collapsed line breaks into spaces, turning mid-word PDF wraps such as `금\n액` and `필요\n하다` into mismatches. Updated the comparison helper in `tests/test_ingest.py` to ignore whitespace while preserving all other characters. Added checks that changed amounts and negation are still rejected, plus runtime-copy, additional PDF/CLI failure, and offline checks. The final 35-test suite passed. The PDF/evaluation content and ingestion text were not changed to accommodate the tests.

## Design Decisions

- Use `documents/` for runtime PDFs and `eval/questions.json` for evaluation. Keep the reviewed originals under `rag_mvp_sample_documents/`; compare the copies again when data changes.
- Extract each page before splitting. A page number means the physical PDF page, starting at 1.
- Begin with a chunk size of 800 characters and an overlap setting of 120. These are initial settings, not measured optimum values; the splitter does not guarantee exactly 120 characters of overlap for every pair.
- Generate stable IDs from source filename, page, position within the page, and chunk text. Phase 2 must separately handle stale chunks and index replacement when documents or settings change.
- Keep dry runs independent of API keys and Streamlit. At Phase 1 completion the CLI required `--dry-run`; Phase 2 subsequently added full indexing while preserving this offline path.
- Treat quote matching as dataset integrity verification. It does not measure retrieval quality or prove that a complete answer fits in a retrieved chunk.

## Reproduce the verification

Run from the project root in PowerShell. The local `.venv` already exists; create it only when setting up a fresh checkout.

```powershell
# Fresh checkout only
py -3.12 -m venv .venv

# Install and check the Phase 1 dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check

# Preview the real corpus and run the offline tests
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

The dry run writes `data/chunks_preview.json` and reports document, page, skipped-page, and chunk counts. That file is an ignored local preview, not a vector index. Full indexing without `--dry-run` was added in Phase 2; the commands above remain valid, and the current test suite also includes later-phase checks. `-X utf8` keeps Korean diagnostic text readable in the verification environment.

Verified direct dependency versions: PyMuPDF **1.28.2**, langchain-core **1.6.10**, langchain-text-splitters **1.1.3**, and pytest **9.1.1**. These results cover the local Windows environment; Cloud compatibility remains unverified.

## Handoff to Phase 2

Phase 1 handed off **22 validated chunks** to [Phase 2](Phase2_IndexingAndRetrieval.md). Phase 2 subsequently completed real local-model indexing and q01/q07/q08 retrieval acceptance on 2026-10-14. Search quality, answer quality, and Cloud compatibility were not measured in Phase 1.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the phase plan and recorded existing initial code, installed dependencies, and unexecuted verification. Implementation was paused at the user's documentation-only request. |
| 2026-10-13 | Completed tasks 1.1–1.5; corrected PDF whitespace comparison, passed 35 tests, reviewed page/chunk evidence and PDF layouts, and recorded the verified local results. |
| 2026-10-13 | Updated handoff and CLI notes for Phase 2; retained the original Phase 1 measurements as historical verification. |

---

# Phase 1 — 개발 기반 및 문서 전처리 `✅ 완료`

> 임베딩 API 사용에 앞서 로컬 환경, PDF 추출, 페이지 메타데이터, 청크 분할을 검증한다.

**완료일**: 2026-10-13\
**상태**: ✅ 완료 — Task 5개와 필수 로컬 검증 통과.\
**선행 조건**: 검토한 MVP 기획서, 샘플 PDF 4개, 평가 질문 10개.\
**기술 구성**: Python 3.12, PyMuPDF, langchain-text-splitters, pytest.

## 개요

고정 데모 문서를 오프라인에서 반복 처리할 수 있는 입력 파이프라인을 준비한다. 각 청크에는 실제 파일명과 물리적 페이지 번호가 남아야 한다. 평가 질문과 정답은 전처리 입력에서 분리한다.

전체 순서는 **개발 기반 → 인덱싱·검색 → 근거 기반 답변 → Streamlit 화면 → 평가·추적·배포**다. 이 문서에는 Phase 1의 상세 Task와 결과를 기록하며, 후속 Phase는 해당 구현을 시작하기 전에 구체화한다. 요구사항의 기준은 [MVP 기획서](../plan/enterprise_rag_assistant_streamlit_mvp_plan.md)다.

## 산출물 및 현재 구현

| 산출물 | 현재 확인한 내용 | 상태 |
| --- | --- | --- |
| 로컬 환경 | `.python-version`, `requirements.txt`, `requirements-dev.txt`; Python 3.12.10 환경, 의존성 파일 기준 설치, `pip check` | ✅ 로컬 검증 완료 |
| 실행용 문서와 평가 데이터 | `documents/`의 PDF 4개, `eval/questions.json`의 질문 10개; 파일 5개 모두 검토 원본과 일치 | ✅ 검증 완료 |
| 공통 설정 | `config.py`: 프로젝트 기준 경로, 청크 800자, 중복 설정 120자 | ✅ 프로젝트 밖 실행까지 검증 |
| 오프라인 전처리 | `ingest.py`: `extract_pages`, `split_pages`, `prepare_corpus`, `PreparedCorpus`, `--dry-run` CLI | ✅ 미리보기 생성·검증 완료 |
| 전처리 테스트 | `tests/test_ingest.py`: 실제 문서, 근거 발췌, 메타데이터, ID, 잘못된 입력, CLI, 오프라인 동작 | ✅ 테스트 35개 통과 |

Phase 1에서는 Chroma 인덱스, 임베딩 호출, 생성 답변, RAG 평가 결과를 만들지 않았다. 이후 구현과 제공업체 검사는 [Phase 2](Phase2_IndexingAndRetrieval.md)에 기록한다.

## Task 및 검증

| Task | 작업 내용 | 완료 기준 | 검증 방법 | 상태 |
| --- | --- | --- | --- | --- |
| 1.1 | Python 환경과 설치 의존성 버전 확인 | 안내된 환경을 설치할 수 있고 의존성 충돌이 없음 | `python --version`, `python -m pip check`, 아래 설치 절차 | ✅ 통과 |
| 1.2 | 실행용 복사본 확인 및 평가 데이터 분리 | 실행용 PDF 4개와 평가 JSON이 검토한 원본과 일치하고, 전처리는 지정 폴더 바로 아래의 PDF만 읽음 | 파일 해시 비교, 실제 문서 및 입력 분리 테스트 | ✅ 통과 |
| 1.3 | 추출 결과와 물리적 페이지 번호 검증 | 샘플 13페이지 모두 텍스트를 추출하며, 빈 페이지를 건너뛰어도 이후 번호가 바뀌지 않음 | Dry run, 실제 문서 테스트, 빈 페이지 테스트 | ✅ 통과 |
| 1.4 | 페이지별 청크와 안정적인 ID 검증 | 비어 있지 않은 청크가 크기 제한을 지키고 한 페이지에 속하며, `source_file`, `page`, `chunk_id`를 재현 가능하게 보존함 | 미리보기 확인, 출처·ID 테스트 | ✅ 통과 |
| 1.5 | 입력 오류 및 CLI 동작 검증 | 경로 누락, 빈 폴더, 손상·암호화·전체 무텍스트 문서를 명확히 처리하며, 프로젝트 밖에서도 CLI 실행 가능 | 오류 입력 및 CLI 테스트, 잘못된 입력의 0이 아닌 종료 코드 확인 | ✅ 통과 |

**결과**: 2026-10-13 Windows의 Python 3.12.10 환경에서 검증했다. `requirements-dev.txt` 기준 설치가 성공했고 `pip check`에서 의존성 충돌이 없었다. 최종 pytest는 종료 코드 0, **35 passed in 2.75s**를 기록했다. Dry run도 정상 종료해 메모리의 문서 데이터와 일치하는 UTF-8 JSON 미리보기를 생성했다. Phase 1의 필수 로컬 검증을 모두 완료했으며, 프로젝트에서 별도 사용자 인수 절차를 요구하지 않는다.

## 검증 결과 보고

| PDF | 물리적 페이지 | 텍스트 추출 페이지 | 청크 |
| --- | ---: | ---: | ---: |
| `01_purchase_process.pdf` | 3 | 3 | 6 |
| `02_approval_budget.pdf` | 3 | 3 | 4 |
| `03_it_security.pdf` | 3 | 3 | 6 |
| `04_contract_settlement.pdf` | 4 | 4 | 6 |
| **합계** | **13** | **13** | **22** |

- **정합성:** PDF 4개와 평가 JSON 모두 검토 원본과 일치한다. 실제 문서에서 제외한 페이지는 0개다. 청크 ID 22개는 중복 없이 재현 가능하며 실제 원본 페이지를 보존한다. 청크 길이는 **149~797자**다.
- **근거 보존:** **근거 그룹 11개**의 **발췌 20개**가 레이아웃 공백을 제외하면 지정 페이지와 모두 일치했다. 별도 검사로 각 발췌 전체가 해당 페이지의 생성 청크 하나 이상에도 포함됨을 확인했다. 이는 문서 내 근거 보존 확인이며 검색 Hit@3나 답변 정확도 측정은 아니다.
- **화면·텍스트 대조:** `02_approval_budget.pdf` 1쪽 결재 표, `01_purchase_process.pdf` 3쪽 수정 FAQ, `03_it_security.pdf` 1쪽 보안 기준을 PDF 렌더링 화면과 대조했다. 결재 금액·결재권자, FAQ의 300만원 조건, 보안 검토 문구가 올바른 읽기 순서로 남아 있다.
- **실패 상황:** 경로 누락·빈 폴더, 손상·0바이트·암호화·전체 무텍스트 PDF, 정상 문서와 손상 파일의 혼재, 잘못된 청크 설정, 쓸 수 없는 출력 경로를 확인했다. CLI는 실패 시 0이 아닌 종료 코드를 반환하며, 검사한 쓰기 전 실패 상황에서는 기존 미리보기를 보존한다.
- **입력·실행 분리:** PDF 이외 파일과 하위 평가 폴더의 PDF는 제외된다. API 인증 환경변수를 제거하고 소켓 연결·DNS 진입점을 테스트에서 차단한 상태에서도 Dry run이 성공했다. 프로젝트 밖 경로에서의 CLI 실행도 통과했다.
- **생성 파일:** `data/chunks_preview.json`을 로컬에 생성했다(31,633바이트). 해당 파일은 Git 제외 대상이며 가상환경과 시크릿 파일 경로의 Git 제외도 확인했다.

### 발견한 실패와 수정

첫 실행은 **24개 통과·2개 실패**였다. q04·q07의 발췌 비교에서 줄바꿈을 공백으로 바꾸면서 `금\n액`, `필요\n하다`처럼 단어 중간에서 줄을 바꾼 PDF 문구를 불일치로 처리했다. `tests/test_ingest.py`의 비교 함수를 공백만 무시하고 다른 문자는 모두 보존하도록 수정했다. 금액과 부정을 변경하면 여전히 불일치로 검출하는 검사, 원본·복사본 일치 검사, 추가 PDF·CLI 오류 검사, 오프라인 검사를 보완했다. 최종 35개 테스트가 모두 통과했다. 테스트 통과를 위해 PDF·평가 내용이나 전처리 본문을 변경하지 않았다.

## 설계 결정 사항

- 실행용 PDF는 `documents/`, 평가 데이터는 `eval/questions.json`을 사용한다. 검토 원본은 `rag_mvp_sample_documents/`에 보존하며, 데이터 변경 시 복사본 일치를 다시 확인한다.
- 페이지를 먼저 추출하고 그 안에서 분할한다. 페이지 번호는 1부터 시작하는 PDF의 물리적 페이지를 뜻한다.
- 청크 크기 800자, 중복 설정 120자로 시작한다. 최적값을 측정한 것은 아니며, 분할기가 모든 인접 청크에 정확히 120자의 중복을 보장하지는 않는다.
- 원본 파일명, 페이지, 페이지 내 청크 순서, 본문으로 안정적인 ID를 만든다. 문서나 설정 변경 시 이전 청크 제거와 인덱스 교체는 Phase 2에서 별도로 처리해야 한다.
- Dry run은 API 키와 Streamlit 없이 실행하도록 구성한다. Phase 1 완료 당시에는 CLI에 `--dry-run`이 필요했고, 이후 Phase 2에서 이 오프라인 경로를 유지하며 실제 인덱싱을 추가했다.
- 근거 발췌 일치 검사는 평가 데이터의 정합성 검증이다. 검색 품질을 측정하거나 검색 청크 안에 완전한 답이 들어 있음을 입증하지는 않는다.

## 검증 재현 방법

프로젝트 루트의 PowerShell에서 실행한다. 현재 로컬 `.venv`는 이미 생성되어 있으므로 새로 내려받은 환경에서만 가상환경을 만든다.

```powershell
# 새로운 환경에서만 실행
py -3.12 -m venv .venv

# Phase 1 의존성 설치 및 확인
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check

# 실제 문서 미리보기 및 오프라인 테스트
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

Dry run은 `data/chunks_preview.json`을 저장하고 문서·페이지·제외 페이지·청크 수를 출력한다. 해당 파일은 Git에서 제외하는 로컬 미리보기이며 벡터 인덱스가 아니다. `--dry-run` 없는 실제 인덱싱은 Phase 2에서 추가했다. 위 명령은 계속 사용할 수 있으며 현재 테스트 모음에는 후속 Phase 검사도 포함된다. `-X utf8`은 검증 환경에서 한국어 진단 문구가 깨지지 않도록 사용한다.

검증한 직접 의존성 버전은 PyMuPDF **1.28.2**, langchain-core **1.6.10**, langchain-text-splitters **1.1.3**, pytest **9.1.1**이다. 이번 결과는 로컬 Windows 환경 기준이며 Cloud 호환성은 아직 검증하지 않았다.

## Phase 2 진입 조건

**검증된 청크 22개**를 [Phase 2](Phase2_IndexingAndRetrieval.md)에 전달했다. 이후 Phase 2는 2026-10-14 실제 로컬 모델 인덱싱과 q01·q07·q08 검색 인수 검증을 완료했다. 검색 품질, 답변 품질, Cloud 호환성은 Phase 1에서 측정하지 않았다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | Phase 계획을 신규 작성하고 기존 초기 코드, 의존성 설치, 미실행 검증 항목을 기록함. 문서 작성으로 범위를 조정한 사용자 요청에 따라 구현 작업을 멈춤. |
| 2026-10-13 | Task 1.1~1.5 완료. PDF 공백 비교를 수정하고 테스트 35개 통과, 페이지·청크 근거와 PDF 화면 대조, 실제 로컬 검증 결과를 기록함. |
| 2026-10-13 | Phase 2 진행에 맞게 전달 상태와 CLI 설명을 갱신하고 기존 Phase 1 측정값은 당시의 검증 기록으로 보존함. |
