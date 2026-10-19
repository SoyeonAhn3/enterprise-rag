# Phase 4 — Streamlit Interface `✅ Completed`

> Make the verified RAG pipeline usable through a simple Korean chat interface.

**Status**: ✅ Local implementation and browser verification completed on 2026-10-14 while preparing Phase 5.\
**Prerequisites**: [Phase 3](Phase3_GroundedAnswers.md) provides verified answers, source mappings, abstention, and error behavior.\
**Technology**: Streamlit 1.65.0 in the same Python service as the RAG pipeline.

## Overview

Implemented `app.py` with three example questions, chat input, loading feedback, answers, source expanders, and safe Korean errors. `app_runtime.py` owns shared resources and calls the existing RAG module; theme and layout remain separate from retrieval/generation.

The user requested Phase 5 next; this missing prerequisite was implemented to make the deployment target runnable. No separate frontend or backend was added.

## Deliverables and verification

| Deliverable | Completion criterion | Verification approach |
| --- | --- | --- |
| ✅ Chat flow | Examples/free text produce answers, sources, pages, and excerpts | Actual Edge browser automation: q01/q07 answered, q09 abstained; source expanders and reload checked |
| ✅ Loading and errors | A spinner and sanitized Korean messages distinguish operational errors from abstention | Streamlit AppTest checked provider/configuration errors, blank/overlong input, and repeated interaction |
| ✅ Resource reuse | Reruns reuse the index, model, and Claude client | AppTest verified one resource construction across consecutive questions; access is serialized with a lock |
| ✅ Server settings and limits | No visitor API-key field; bounded question/output/time/session usage | Server settings and 500-character input validated; ten attempts per session by default, including failures |

Implemented files: [app.py](../app.py), [app_runtime.py](../app_runtime.py), [.streamlit/config.toml](../.streamlit/config.toml), [.streamlit/secrets.toml.example](../.streamlit/secrets.toml.example), and [UI tests](../tests/test_app.py). Streamlit was installed without replacing or uninstalling existing packages. Secrets remain server-side.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Browser evidence: [home](../docs/evidence/local-home.png), [answers, excerpts, and abstention](../docs/evidence/local-chat.png). The three real requests took approximately 3.00, 3.82, and 1.43 seconds after RAG initialization. Later public deployment and owner checks are recorded in [Phase 5](Phase5_EvaluationAndDeployment.md).

### Source excerpt line wrapping — 2026-10-14

The security PDF itself splits `금액과` across two physical lines. `ingest.py` preserves the extracted `금\n액과`; `grounding.py` restores the original quote; the old `st.text` display retained that forced break. The PDF, portable index, and saved q07 result all reproduce it.

[source_display.py](../source_display.py) reconnects a split Korean word only when its complete form appears unbroken in the fixed PDFs. Existing spaces, paragraph/list boundaries, and unknown splits remain intact. The four small PDFs are read once per process, with no additional API call. HTML-escaped excerpts use scoped `word-break: keep-all` styling and allow unusually long tokens to wrap. Retrieved text, quotes, PDFs, vectors, and recorded evaluation results remain unchanged. References: [CSS word wrapping](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/word-break), [Streamlit HTML API](https://docs.streamlit.io/develop/api-reference/text/st.html).

The full suite passed **209 tests in 62.00 seconds**, including the actual PDF regression, existing-chat redisplay without generation, evidence preservation, boundaries, and escaped markup. Edge verified `금액과` stays on one line at viewport widths 320/375/768/1200 px and 19 additional excerpt widths. Screenshots of the saved answer: [desktop](../docs/evidence/source-excerpt-fixed-desktop.png), [mobile](../docs/evidence/source-excerpt-fixed-mobile.png).

## All supporting quotations — 2026-10-19

`source_excerpts(result, source)` now returns every distinct validated quotation for that source in claim order, removing whitespace-equivalent duplicates and keeping disjoint passages separate. `app.py` renders them in the source expander with numbered captions when needed. Saved results without claims retain the legacy excerpt fallback. HTML escaping, PDF-aware word wrapping, and the stored result schema are preserved; display adds no model calls.

Four display regression tests were added. The [first saved-answer replay](../eval/results/completeness_display_20261019/display_check.json) checked seven answers, 11 source expanders, and 23 quotations. The [final citation replay](../eval/results/citation_completeness_20261019/display_check.json) checked four answers, nine expanders, and 16 quotations. The full software suite passed **488 tests**. These are local Streamlit AppTest checks; the dated browser screenshots above remain unchanged.

## Decisions and dependencies

- `st.cache_resource` shares caller-owned resources, with idempotent shutdown cleanup. Existing indexes load normally; a fresh deployment imports the reviewed precomputed-vector bundle. It does not re-embed documents at startup.
- Session history may display prior exchanges, but multi-turn memory and query rewriting remain outside scope.
- A session counter is only a basic demo limit and can be bypassed through a new session. Configure provider-side usage controls before public sharing in Phase 5.
- Local browser verification passed. Server/model setting changes require a resource restart. Real local-to-remote LangSmith verification, the public URL, and owner-reported Cloud settings are recorded in [Phase 5](Phase5_EvaluationAndDeployment.md); a fresh Cloud regression after the latest release was not independently observed.

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the UI, resource reuse, settings, and usage-control outline; implementation is pending. |
| 2026-10-14 | Implemented the missing local UI prerequisite during Phase 5 work; AppTest and three live browser questions passed, screenshots saved, bilingual documentation updated. Separate dev-log unavailable. |
| 2026-10-14 | Fixed the reported PDF-split source word with conservative display formatting and Korean word wrapping. Original evidence preserved; 209 tests and browser layout checks passed. Separate dev-log unavailable. |
| 2026-10-19 | Documented all-quotation display, compatibility, and saved-answer replay; synchronized deployment handoff with Phase 5. No new browser or Cloud run; dev-log unavailable. |

---

# Phase 4 — Streamlit 화면 및 사용 흐름 `✅ 완료`

> 검증한 RAG를 간단한 한국어 채팅 화면에서 사용할 수 있게 만든다.

**상태**: ✅ Phase 5 준비 중 2026-10-14 로컬 구현 및 실제 브라우저 검증 완료.\
**선행 조건**: [Phase 3](Phase3_GroundedAnswers.md)의 답변·출처 매핑·보류·오류 동작 검증.\
**기술**: RAG 처리와 같은 Python 서비스에서 실행하는 Streamlit 1.65.0.

## 개요

`app.py`에 예시 질문 3개, 채팅 입력, 로딩 안내, 답변, 출처 펼치기, 민감 정보를 제외한 한국어 오류를 구현했다. `app_runtime.py`가 공유 리소스를 관리하고 기존 RAG 모듈을 호출한다. 테마와 배치는 검색·생성에서 분리했다.

사용자가 Phase 5 진행을 요청했으므로 실행 가능한 배포 대상을 위해 누락된 선행 화면을 구현했다. 별도 프론트엔드나 백엔드는 추가하지 않았다.

## 산출물 및 검증

| 산출물 | 완료 기준 | 검증 방향 |
| --- | --- | --- |
| ✅ 채팅 흐름 | 예시·직접 입력 후 답변·문서명·페이지·발췌 표시 | 실제 Edge 브라우저 자동화에서 q01·q07 답변, q09 보류, 발췌 펼치기와 새로고침 확인 |
| ✅ 로딩·오류 | 처리 중 표시와 한국어 오류로 운영 실패·보류 구분 | AppTest로 API·설정 오류, 빈 질문·길이 초과·연속 입력 확인 |
| ✅ 리소스 재사용 | 재실행 시 인덱스·모델·Claude 클라이언트 재사용 | AppTest에서 연속 질문에도 리소스 1회 생성 확인. 공유 객체는 잠금으로 순차 사용 |
| ✅ 서버 설정·제한 | 방문자 키 입력 없음, 질문·출력·시간·세션 제한 | 서버 설정, 질문 500자, 실패도 차감하는 기본 세션 10회 한도 검증 |

구현 파일: [app.py](../app.py), [app_runtime.py](../app_runtime.py), [.streamlit/config.toml](../.streamlit/config.toml), [.streamlit/secrets.toml.example](../.streamlit/secrets.toml.example), [UI 테스트](../tests/test_app.py). 기존 패키지 교체·삭제 없이 Streamlit을 설치했고 비밀값은 서버에서 관리한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

브라우저 증빙: [초기 화면](../docs/evidence/local-home.png), [답변·발췌·보류](../docs/evidence/local-chat.png). 실제 3회 요청의 RAG 초기화 후 처리 시간은 약 3.00초·3.82초·1.43초였다. 이후 공개 배포와 사용자 확인은 [Phase 5](Phase5_EvaluationAndDeployment.md)에 기록했다.

### 출처 발췌 줄바꿈 수정 — 2026-10-14

보안 PDF 자체에서 `금액과`가 두 물리적 줄로 나뉜다. `ingest.py`가 추출한 `금\n액과`를 보존하고, `grounding.py`가 원문 인용을 복원하며, 기존 `st.text` 화면이 강제 줄바꿈까지 표시한 것이 원인이다. PDF·배포 인덱스·저장된 q07 결과에서 재현했다.

[source_display.py](../source_display.py)는 고정 PDF에 붙여 쓴 전체 단어가 확인될 때만 끊긴 한글 단어를 연결한다. 기존 공백·문단·목록 경계와 판단할 수 없는 줄바꿈은 유지한다. 작은 PDF 4개를 프로세스당 한 번 읽고 API를 추가 호출하지 않는다. 발췌를 HTML 이스케이프한 뒤 해당 영역에만 `word-break: keep-all`을 적용하며, 화면보다 긴 단어에는 넘침 줄바꿈을 허용한다. 검색 원문·인용·PDF·벡터·기록된 평가 결과는 보존한다. 참고: [CSS 단어 줄바꿈](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/word-break), [Streamlit HTML API](https://docs.streamlit.io/develop/api-reference/text/st.html).

실제 PDF 회귀 검사, 생성 없는 기존 대화 재표시, 원문 보존, 경계 유지, HTML 이스케이프를 포함해 전체 테스트 **209개가 62.00초에 통과**했다. Edge에서 화면 폭 320·375·768·1200 px와 발췌 영역 폭 19개를 추가 검사해 `금액과`가 한 줄에 유지됨을 확인했다. 저장된 답변의 수정 화면: [데스크톱](../docs/evidence/source-excerpt-fixed-desktop.png), [모바일](../docs/evidence/source-excerpt-fixed-mobile.png).

## 모든 근거 인용 표시 — 2026-10-19

`source_excerpts(result, source)`는 주장 순서에 따라 해당 출처의 검증된 인용을 모두 반환하고, 공백 차이만 있는 중복을 제거하며 떨어진 발췌를 분리한다. `app.py`는 출처 펼침 영역에서 이를 표시하고 여러 개면 번호를 붙인다. 주장 정보가 없는 과거 저장 답변은 기존 발췌를 표시한다. HTML 이스케이프·PDF 단어 줄바꿈 처리·저장 답변 형식은 유지하며 표시 때문에 모델을 추가 호출하지 않는다.

표시 회귀 테스트 4개를 추가했다. [첫 저장 답변 재생](../eval/results/completeness_display_20261019/display_check.json)에서 답변 7개·출처 영역 11개·인용 23개, [최종 인용 재생](../eval/results/citation_completeness_20261019/display_check.json)에서 답변 4개·출처 영역 9개·인용 16개를 확인했다. 전체 소프트웨어 테스트는 **488개 통과**다. 로컬 Streamlit AppTest 결과이며 위의 과거 브라우저 스크린샷은 갱신하지 않았다.

## 결정 사항 및 의존성

- `st.cache_resource`로 리소스를 공유하고 종료 시 중복 정리를 방지한다. 기존 인덱스를 로드하며 신규 배포는 검토한 사전 계산 벡터 번들을 가져온다. 시작 시 문서를 다시 임베딩하지 않는다.
- 이전 대화를 화면에 표시하는 세션 기록은 선택 사항이다. 다중 턴 기억과 질문 재작성은 범위에서 제외한다.
- 세션 횟수 제한은 새 세션으로 우회 가능한 간이 보호다. Phase 5에서 공개 공유 전에 제공업체 사용량 제어도 설정한다.
- 로컬 브라우저 검증을 통과했다. 서버·모델 설정 변경 시 리소스를 재시작한다. 실제 로컬 실행의 LangSmith 원격 대조, 공개 URL, 사용자 보고 기준 Cloud 설정은 [Phase 5](Phase5_EvaluationAndDeployment.md)에 기록했다. 최신 게시본의 새 Cloud 회귀 실행은 별도로 관측하지 않았다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 화면·리소스 재사용·설정·사용량 제한의 개요 신규 작성. 구현은 후속 진행 대상으로 기록함. |
| 2026-10-14 | Phase 5 중 누락된 로컬 화면 선행 조건 구현. AppTest·실제 브라우저 3문항 통과, 스크린샷 보존, 영문·국문 문서 갱신. 별도 dev-log 미설치. |
| 2026-10-14 | 제보된 출처 단어 끊김을 보수적인 표시 보정·한국어 단어 줄바꿈으로 수정. 원문 증빙 보존, 테스트 209개·브라우저 배치 검사 통과. 별도 dev-log 미설치. |
| 2026-10-19 | 모든 인용 표시·호환성과 저장 답변 화면 재생을 기록하고 Phase 5 배포 전달 상태를 갱신했다. 새 브라우저·Cloud 실행은 하지 않았으며 별도 dev-log 미설치. |
