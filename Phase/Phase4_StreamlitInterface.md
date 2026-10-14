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

Browser evidence: [home](../docs/evidence/local-home.png), [answers, excerpts, and abstention](../docs/evidence/local-chat.png). The three real requests took approximately 3.00, 3.82, and 1.43 seconds after RAG initialization. Public Cloud operation is a separate Phase 5 gate.

## Decisions and dependencies

- `st.cache_resource` shares caller-owned resources, with idempotent shutdown cleanup. Existing indexes load normally; a fresh deployment imports the reviewed precomputed-vector bundle. It does not re-embed documents at startup.
- Session history may display prior exchanges, but multi-turn memory and query rewriting remain outside scope.
- A session counter is only a basic demo limit and can be bypassed through a new session. Configure provider-side usage controls before public sharing in Phase 5.
- Local browser verification passed. Server/model setting changes require a resource restart. LangSmith, public URL, and Cloud restart verification remain tracked in [Phase 5](Phase5_EvaluationAndDeployment.md).

## Change Log

| Date | Description |
| --- | --- |
| 2026-10-13 | Created the UI, resource reuse, settings, and usage-control outline; implementation is pending. |
| 2026-10-14 | Implemented the missing local UI prerequisite during Phase 5 work; AppTest and three live browser questions passed, screenshots saved, bilingual documentation updated. Separate dev-log unavailable. |

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

브라우저 증빙: [초기 화면](../docs/evidence/local-home.png), [답변·발췌·보류](../docs/evidence/local-chat.png). 실제 3회 요청의 RAG 초기화 후 처리 시간은 약 3.00초·3.82초·1.43초였다. 공개 Cloud 동작은 별도의 Phase 5 완료 조건이다.

## 결정 사항 및 의존성

- `st.cache_resource`로 리소스를 공유하고 종료 시 중복 정리를 방지한다. 기존 인덱스를 로드하며 신규 배포는 검토한 사전 계산 벡터 번들을 가져온다. 시작 시 문서를 다시 임베딩하지 않는다.
- 이전 대화를 화면에 표시하는 세션 기록은 선택 사항이다. 다중 턴 기억과 질문 재작성은 범위에서 제외한다.
- 세션 횟수 제한은 새 세션으로 우회 가능한 간이 보호다. Phase 5에서 공개 공유 전에 제공업체 사용량 제어도 설정한다.
- 로컬 브라우저 검증을 통과했다. 서버·모델 설정 변경 시 리소스를 재시작한다. 실제 LangSmith, 공개 URL, Cloud 재시작 검증은 [Phase 5](Phase5_EvaluationAndDeployment.md)에 남아 있다.

## 변경 이력

| 날짜 | 내용 |
| --- | --- |
| 2026-10-13 | 화면·리소스 재사용·설정·사용량 제한의 개요 신규 작성. 구현은 후속 진행 대상으로 기록함. |
| 2026-10-14 | Phase 5 중 누락된 로컬 화면 선행 조건 구현. AppTest·실제 브라우저 3문항 통과, 스크린샷 보존, 영문·국문 문서 갱신. 별도 dev-log 미설치. |
