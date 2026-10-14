# Phase 5 — Evaluation, Tracing, and Deployment `🚧 In Progress`

> Demonstrate the application with measured results, a real trace, and a working public URL.

**Status**: 🚧 Local implementation and ten-question evaluation verified on 2026-10-14. Human review, a real LangSmith trace, and public Cloud verification remain pending.\
**Prerequisites**: [Phase 4](Phase4_StreamlitInterface.md) works locally; API access, a LangSmith project, and GitHub/Streamlit deployment access are available.\
**Planned technology**: Python evaluation runner, JSON results, manual grading, LangSmith, Streamlit Community Cloud.

## Overview

Evaluate the fixed ten-question dataset, inspect retrieval and generation traces, and deploy the same verified corpus and settings. Publish actual results and limitations in both READMEs so a portfolio reviewer can reproduce the workflow and assess its quality.

The missing Phase 4 interface was implemented and verified locally first. The user selected `https://github.com/SoyeonAhn3/enterprise-rag.git` and confirmed the Streamlit/GitHub account connection. Claude credentials work locally; LangSmith credentials are not configured, and no public URL has been established.

## Tasks and current evidence

| Deliverable | Completion criterion | Verification approach |
| --- | --- | --- |
| ✅ Evaluation runner | Ten results retain retrieval, answers, settings, errors, and timing; metrics are reproducible | Real ten-question baseline completed; checkpoint/error/denominator/integrity tests passed |
| 🚧 Review | All ten answers are checked against criteria with evidence notes; identify the reviewer accurately | Agent review recorded 9/10 correctness and 10/10 grounding; blank report-bound human review remains pending |
| 🚧 LangSmith | Separate retrieval/generation spans; tracing failure does not break answers; verify one real remote tree | SDK HTTP contract and every write-failure position tested; real key absent, so remote verification not run |
| 🚧 Public deployment | Public key-free visitor flow and index reload after restart | Local real browser passed; portable index import/reload passed; GitHub publication and Cloud execution pending |
| 🚧 Portfolio evidence | Actual measurements, failure analysis, screenshots, trace/public links | Bilingual docs, local screenshots, and saved JSON ready; live URL/trace evidence remain absent |

Implemented [eval/evaluate.py](../eval/evaluate.py), [tracing.py](../tracing.py), [eval/check_trace.py](../eval/check_trace.py), [deployment.py](../deployment.py), the portable index bundle, Streamlit settings/interface, tests, and [deployment instructions](../DEPLOYMENT.md). Existing packages were preserved when Streamlit was installed; `pip check` found no broken requirements. `.env` gained only missing optional tracing/session settings, preserving the Claude key.

The complete local suite passed **205 tests in 17.03 seconds** on 2026-10-14. This automated result is separate from the ten live Claude requests and the three real browser questions below.

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

Tracing is opt-in. Explicit root, `retrieval`, and `generation` runs contain question/context/output, not settings or credentials. Writes use bounded network settings; the first failure disables that sink until restart, while ordinary answers continue. `check_trace` reads the remote tree back and requires both completed child runs plus matching output; a successful POST alone is not proof of a verified trace. The local check currently stops before Claude because no LangSmith key is configured.

The 208,225-byte [index bundle](../deployment/index_bundle.json) stores the 22 original chunks and precomputed 384-dimensional vectors. It imports into an empty Chroma directory, verifies integrity, and reuses the index on restart. Fresh-import retrieval succeeded with the real query model while document embedding was forbidden. PDFs, settings, and the original local index were not rebuilt. Linux/Cloud behavior remains unverified because the local Docker Linux daemon was unavailable.

Actual local Edge browser automation verified q01/q07 answers, q09 abstention, source expanders, and reload. Screenshots: [home](../docs/evidence/local-home.png), [chat](../docs/evidence/local-chat.png). Full Cloud instructions and remaining operator steps are in [DEPLOYMENT.md](../DEPLOYMENT.md).

## Evaluation contract

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
- This phase remains in progress while required live URL checks, manual grading, or trace evidence are missing. Document any account/access blocker specifically; code completion alone does not satisfy deployment completion.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the evaluation contract and portfolio/deployment completion criteria; all execution evidence remains pending. |
| 2026-10-14 | Implemented evaluation, error-isolated tracing, remote trace verifier, portable index, and the missing local UI. Recorded 10 live results, agent review, local browser evidence, and deploy instructions. Human review, LangSmith credentials, and public deployment remain pending. Separate dev-log unavailable. |

---

# Phase 5 — 평가·실행 추적·배포 `🚧 진행 중`

> 실제 평가 결과, 실행 Trace, 공개 URL로 애플리케이션을 검증하고 보여준다.

**상태**: 🚧 2026-10-14 로컬 구현·실제 10문항 평가 검증. 사람 검토, 실제 LangSmith Trace, 공개 Cloud 검증은 대기.\
**선행 조건**: [Phase 4](Phase4_StreamlitInterface.md) 로컬 동작 검증, API 사용 준비, LangSmith 프로젝트, GitHub·Streamlit 배포 접근 권한.\
**예정 기술**: Python 평가 실행 코드, JSON 결과, 수동 채점, LangSmith, Streamlit Community Cloud.

## 개요

고정 질문 10개를 평가하고 검색·생성 Trace를 확인한 뒤 같은 문서와 검증한 설정으로 배포한다. 양쪽 README에 실측 결과와 한계를 기록해 포트폴리오 검토자가 실행 흐름을 재현하고 품질을 판단할 수 있게 한다.

누락된 Phase 4 화면을 먼저 구현하고 로컬 검증했다. 사용자가 `https://github.com/SoyeonAhn3/enterprise-rag.git`를 지정하고 Streamlit·GitHub 계정 연결을 확인했다. 로컬 Claude 키는 동작하며 LangSmith 키는 미설정이고 공개 URL은 아직 없다.

## Task 및 현재 증빙

| 산출물 | 완료 기준 | 검증 방향 |
| --- | --- | --- |
| ✅ 평가 실행 | 10회 결과에 검색·답변·설정·오류·시간 보존 및 지표 재현 | 실제 10문항 완료. 중간 저장·실패·분모·무결성 테스트 통과 |
| 🚧 검토 | 검토자를 정확히 구분하고 전체 답변을 근거·채점 기준에 대조 | 에이전트 검토 정답 9/10·근거 충족 10/10 기록. 해당 결과에 연결된 사람 검토 양식은 미작성 |
| 🚧 LangSmith | 검색·생성 분리, 추적 오류 시 답변 유지, 실제 원격 실행 확인 | SDK HTTP 계약·모든 전송 단계 실패 테스트 통과. 실제 키가 없어 원격 검증 미실행 |
| 🚧 공개 배포 | 방문자 키 없는 공개 사용 흐름 및 재시작 후 인덱스 로딩 | 실제 로컬 브라우저·번들 가져오기 및 재로딩 통과. GitHub 게시·Cloud 실행 대기 |
| 🚧 포트폴리오 | 실측·실패 분석·스크린샷·실제 추적 및 공개 링크 | 영문·국문 문서·로컬 스크린샷·JSON 준비. 실제 공개 URL·Trace 증빙은 아직 없음 |

구현 파일: [eval/evaluate.py](../eval/evaluate.py), [tracing.py](../tracing.py), [eval/check_trace.py](../eval/check_trace.py), [deployment.py](../deployment.py), 사전 계산 인덱스 번들, Streamlit 설정·화면, 테스트, [배포 안내](../DEPLOYMENT.md). 기존 패키지를 교체하지 않고 Streamlit을 설치했고 `pip check`에서 충돌이 없었다. `.env`에는 누락된 선택적 추적·세션 설정만 추가해 Claude 키를 보존했다.

2026-10-14 전체 로컬 테스트는 **205개, 17.03초**로 통과했다. 이 자동 검사 결과는 아래 실제 Claude 10문항 평가 및 실제 브라우저 3문항과 별개다.

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

추적은 선택적으로 켠다. 루트·`retrieval`·`generation`에 질문·문맥·출력을 기록하며 키·설정 객체는 넣지 않는다. 네트워크 요청을 제한하고 첫 전송 실패부터 재시작 전까지 해당 추적기를 중단해도 답변은 유지한다. `check_trace`는 실제 원격 실행을 재조회하여 두 하위 실행 완료와 답변 일치를 확인한다. POST 성공만을 Trace 검증으로 간주하지 않는다. 현재는 LangSmith 키가 없어 Claude 호출 전에 검사를 중단한다.

208,225바이트 [인덱스 번들](../deployment/index_bundle.json)은 원래 청크 22개와 384차원 사전 계산 벡터를 담는다. 빈 Chroma 폴더에 가져와 무결성을 검증하고 이후 재사용한다. 문서 임베딩을 금지한 채 신규 가져오기와 실제 질문 모델 검색에 성공했다. PDF·설정·기존 로컬 인덱스를 재생성하지 않았다. 로컬 Docker Linux 데몬이 실행되지 않아 Linux·Cloud 동작은 아직 미검증이다.

실제 로컬 Edge 브라우저 자동화로 q01·q07 답변, q09 보류, 출처 펼치기, 새로고침을 확인했다. 스크린샷: [초기 화면](../docs/evidence/local-home.png), [대화](../docs/evidence/local-chat.png). Cloud 설정과 남은 운영자 절차는 [DEPLOYMENT.md](../DEPLOYMENT.md)에 있다.

## 평가 기준

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
- 필수 공개 URL 확인, 수동 채점, Trace 증빙이 남아 있으면 진행 중 상태를 유지한다. 계정·접근 권한 제약이 있으면 구체적으로 기록하며 코드 완성만으로 배포 완료를 선언하지 않는다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 평가 기준과 포트폴리오·배포 완료 조건 신규 작성. 실행 증빙은 모두 후속 검증 대상으로 기록함. |
| 2026-10-14 | 평가 실행·오류를 분리한 추적·원격 검증기·인덱스 번들·누락된 로컬 화면 구현. 실제 10문항·에이전트 검토·브라우저 증빙·배포 안내 기록. 사람 검토·LangSmith 키·공개 배포는 대기. 별도 dev-log 미설치. |
