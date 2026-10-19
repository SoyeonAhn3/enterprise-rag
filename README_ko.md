🌐 [한국어](./README_ko.md) | [English](./README.md)

# Enterprise RAG Assistant

> 회사 규정 PDF에 대해 질문하면, 검증된 출처와 함께 한국어로 답하는 RAG 데모입니다.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-%EB%B0%94%EB%A1%9C%20%EC%8B%A4%ED%96%89-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://enterprise-rag-demo-project.streamlit.app/)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.65-FF4B4B?logo=streamlit&logoColor=white)
![Claude](https://img.shields.io/badge/LLM-Claude-D97757?logo=anthropic&logoColor=white)
![Chroma](https://img.shields.io/badge/Vector%20DB-Chroma-327EFF)

> 🚀 **바로 사용해 보기:** **[enterprise-rag-demo-project.streamlit.app](https://enterprise-rag-demo-project.streamlit.app/)** — 회원가입·API 키 없이 바로 질문할 수 있습니다.
> 앱이 잠들어 있으면 **"Yes, get this app back up!"** 버튼을 누르고 1분 정도 기다려 주세요.

## 개요

**해결하려는 문제.** *"부가세 제외 구매 금액이 정확히 100만원이면 최종 결재권자는 누구인가?"* 같은 규정 질문은 여러 문서에 흩어진 금액 기준과 조건을 정확히 알아야 답할 수 있습니다. LLM이 기억에 의존해 답하면 없는 규정을 만들거나 조건을 빠뜨릴 수 있습니다.

**접근 방식.** 고정된 PDF에서 근거를 검색하고, Claude가 그 근거만으로 답하게 한 뒤, 인용한 원문이 실제 검색 결과와 일치하는지 검증하고 나서 화면에 보여 줍니다. 문서에 답이 없으면 답변을 보류합니다.

**프로젝트 성격.** 포트폴리오 프로젝트입니다. RAG를 이해하고 구현했는지, 정확도를 **실제로 측정**했는지, 근거를 정교하게 처리하고 개선 이유를 설명할 수 있는지 보여 주는 것이 목표입니다. Streamlit은 시연 화면이며 사용성 확대와 동시 접속 검사는 현재 범위에 포함하지 않습니다. 모든 문서는 가상 기업 **가온비즈(Gaonbiz)**의 합성 규정입니다.

| 문서 | 페이지 | 주제 |
| --- | ---: | --- |
| [구매요청 및 발주 업무지침](rag_mvp_sample_documents/01_purchase_process.pdf) | 3 | 구매 요청, 비교견적, 발주, 긴급 구매 |
| [결재권한 및 예산통제 규정](rag_mvp_sample_documents/02_approval_budget.pdf) | 3 | 금액별 결재권자, 예산 검토, 구매 분할 금지 |
| [IT 자산 및 SaaS 보안검토 지침](rag_mvp_sample_documents/03_it_security.pdf) | 3 | 사전 보안검토, 무료 체험, 자산 등록 |
| [계약 검토·검수·정산 업무가이드](rag_mvp_sample_documents/04_contract_settlement.pdf) | 4 | 법무 검토, 검수, 지급 일정 |

![로컬 Streamlit 첫 화면](docs/evidence/local-home.png)

## 목차

- [동작 흐름](#동작-흐름)
- [평가 결과](#평가-결과)
- [기술 스택](#기술-스택)
- [AI 구성 요소](#ai-구성-요소)
- [빠른 시작](#빠른-시작)
- [테스트](#테스트)
- [프로젝트 구조](#프로젝트-구조)
- [현재 상태](#현재-상태)
- [한계점](#한계점)
- [향후 계획](#향후-계획)
- [문서](#문서)

## 동작 흐름

**2-Step RAG** 구조입니다. 검색 1회 후 답변 생성 호출 1회로 끝납니다.

```text
[배포 전]  PDF 4개
        ↓  ingest.py: 페이지별 텍스트 추출(PyMuPDF), 약 800자 청크·120자 중복으로 분할
     청크 22개 (각각 source_file · page · chunk_id 메타데이터 포함)
        ↓  로컬 다국어 E5 모델로 임베딩, Chroma에 저장 (사전 계산 번들로 배포)

[질문마다]  Streamlit 채팅에서 사용자 질문
        ↓  rag.py: 질문 임베딩 후 상위 k개 청크 검색
        ↓  (선택형 페이지 모드: 6,000자 한도 안에서 서로 다른 원본 페이지 최대 5개)
        ↓  grounding.py + llm.py: Claude 1회 호출 → 주장별 인용문·출처 ID가 담긴 JSON
        ↓  검증: 인용문이 검색 원문과 일치해야 함. 파일명·페이지는 저장된 메타데이터에서 가져옴
     한국어 답변 + 출처(문서 · 페이지 · 발췌), 또는 답변 보류 메시지
```

## 평가 결과

모든 수치는 **소규모 합성 평가셋**(PDF 4개, 13페이지, 청크 22개)의 결과입니다. 정답 여부는 AI 에이전트가 채점했으며 **사람 검토는 아직 완료되지 않았습니다**.

| 평가 | 질문 수 | 비교 설정 | 결과 |
| --- | --- | --- | --- |
| 기존 기준 평가 (2026-10-14) | 10 | chunks, k=3 | 검색 Hit@3 **8/8** · 답변 보류 **2/2** · AI 채점 정답 **9/10** · 평균 응답 **3.33초** |
| 확대 평가, 개발용 (2026-10-14) | 40 | chunks, k=3 → k=5 | AI 채점 정답 **35/40 → 39/40** |
| 확대 평가, 최종 확인용 (2026-10-14) | 20 | chunks, k=3 → k=5 | AI 채점 정답 **13/20 → 15/20** |
| 페이지 문맥 검색 (2026-10-16) | 답변 가능한 개발용 32개 | chunks k=3 → chunks k=5 → pages k=5 | 필수 근거 전체 확보 **24/32 → 26/32 → 32/32**, 알려진 회귀 사례 AI 채점 **6/6** |
| 조건 고정 쌍별 비교 (2026-10-16) | 60 (답변 가능 48) | chunks k=5 → pages k=5 | 문맥에 필수 근거 전체 확보 **37/48 → 47/48** · 출력 검증 통과 응답 **59/60 → 57/60** · 답변 정확도 **미확정** |
| 마지막 페이지 선택 (2026-10-16, 오프라인) | 같은 알려진 60문항 | 기존 pages k=5 → 질문 표현을 보존하는 선택 | 필수 근거 전체 확보 **47/48 → 48/48** · 전체 근거 확보 악화 없음 · 새 답변·채점 없음 |
| V3 개발용 평가 (2026-10-19) | 20 (답변 가능 16) | chunks k=5 → pages k=5 | 원본 AI 통과 **14/20 → 15/20** · 필수 근거 전체 확보 **10/16 → 12/16** · 출력 검증 통과 **20/20 → 19/20** |
| V3 개발 후속 개선 (2026-10-19) | 같은 개발용 20문항 | 저장 페이지 답변 → 개선 후, 같은 새 채점 기준 | AI 통과 **17/20 → 17/20** · 필수 근거 **12/16 → 14/16** · 출력 검증 **19/20 → 20/20** |
| V3 제한한 최종 점검 (2026-10-19) | 20 (답변 가능 16) | pages/k=5/6,000자 고정; Codex 원문 대조 | 필수 근거 **12/16** · 내용 **15/20** · 내용·주장 인용 모두 **13/20** · 답변 불가 보류 **4/4** |
| 필수 항목·출처 표시 점검 (2026-10-19) | 사용자 질문 5개 + 변형 2개 | pages/k=5/6,000자; Codex 원문 대조 | 핵심 요청 항목 확인, 계좌 확인 자료를 관련 답변 3개에 명시; 화면 재생에서 출처 11개·서로 다른 인용 **23개** 표시 |
| 인용 완전성 집중 점검 (2026-10-19) | 알려진 사례·변형 3개 + 보류 1개 | 같은 검색 설정; 최종 출력 한도 4,096토큰 | 마지막 4문항 실행: **주장별 근거가 있는 답변 3개 + 정상 보류 1개**; 주장 11개·인용 16개 대조 |

[이전 구현](Phase/Phase6_RetrievalAndAnswerQuality.md#채점-분리와-규정-선택-보완--2026-10-19)은 정확성 채점과 검색 근거만 보는 근거성 채점을 분리하고, 문맥 선택에서 규정 주제를 묶습니다. 오프라인 개발용 필수 근거는 **14/16→16/16**, 알려진 v2는 **48/48**을 유지했습니다. 실제 채점은 부분 완료로 요청 10회·채택 6개 단계·검증 거부 3개·제공업체 오류 1개입니다. 같은 모델의 판정 불일치가 남아 있으며 새 답변의 정확도 향상을 주장하지 않습니다.

수치를 읽을 때 주의할 점:

- **기존 평가의 90%만 따로 보지 마세요.** 20문항 최종 확인용에서는 정답률이 65%(k=3), 75%(k=5)였습니다.
- **같은 채점 기준으로 구현을 비교합니다.** 후속 개선은 이전 페이지 답변 20개를 재사용하고 새 답변 20회·채점 39회, 총 모델 59회를 새로 호출했습니다. 같은 새 기준에서 양쪽 모두 17/20입니다. 이전 답변의 원래 점수 15/20은 다른 채점 지시의 결과이므로 재채점 상승을 구현 개선으로 보지 않습니다. 근거·출력 검증은 좋아졌지만 전체 정확도 개선은 미입증이며 참고 정답 오용·추론 판정의 불일치도 검토해야 합니다.
- **이전 60문항 비교의 채점은 여전히 미완료입니다.** 완료 29건, 잔액 부족으로 실패한 87건, 검증 실패 후 건너뛴 4건입니다. 이번 v3 실행에서는 해당 과거 답변을 재채점하지 않았으며 일부 통과 건수는 정답률이 아닙니다.
- **이전 평가의 답변 생성과 채점은 같은 Claude 모델이 수행했습니다**(별도 호출). 사람 검토 대기 목록 34건이 남아 있습니다.
- **이미 확인한 사례이며 독립 평가가 아닙니다.** 확대 평가 60문항은 개발 중 모두 확인했으므로 Phase 6 결과는 진단 지표이지 정답률 추정이 아닙니다. 페이지 모드는 chunks/k=5보다 평균 문맥 글자 수가 34.39% 많습니다.
- **참고 정답은 답변 생성에 전달되지 않습니다.** 파이프라인에는 질문만 들어가며, 참고 정답·근거 주석·채점 기준은 채점에만 사용합니다.

근거 자료: [기존 평가 원본](eval/results/phase5_baseline.json) · [AI 검토 기록](eval/results/phase5_agent_review.json) · [60문항 보고서](eval/results/phase5_v2_20261014/report.md) · [페이지 문맥 보고서](eval/results/phase6_20261016/report.md) · [조건 고정 비교 보고서](eval/results/phase6_quality_20261016/report.md) · [채점 복구 계획](eval/results/phase6_review_recovery_selection_20261016/plan.json)

이전 고정 평가: [제한한 최종 보고서와 사람 검토 문항](eval/results/v3_closeout_20261019/report.md) · [요약](eval/results/v3_closeout_20261019/summary.json) · [검증](eval/results/v3_closeout_20261019/verification.json). 개발 6개·최종 20개 답변을 생성했고 별도 AI 채점 호출은 없습니다. 최종 평균 응답은 5.193초입니다. 해당 결과와 수치는 그대로 보존했습니다.

최신 집중 보완: [필수 항목 검토](eval/results/completeness_display_20261019/review.json)와 [전체 시도를 포함한 인용 검토](eval/results/citation_completeness_20261019/review.json). 첫 점검은 답변 7회를 호출했습니다. 인용 보완은 초기 2,048토큰 한도 초과, 내용·인용 문제가 1건 남은 재점검, 마지막 4문항 통과까지 총 10회를 호출했습니다. 별도 AI 채점과 자동 재시도는 없습니다. 관측한 사례를 보고 보완했으므로 회귀 점검이며 새로운 독립 정답률이 아닙니다. Codex 원문 대조는 독립 사람 채점을 대신하지 않습니다.

저장된 결과를 모델 호출·인증 정보 없이 오프라인으로 검증하려면:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/phase6_quality_20261016
.\.venv\Scripts\python.exe -X utf8 -m eval.refinement verify --output-dir eval/results/v3_refinement_dev_20261019
.\.venv\Scripts\python.exe -X utf8 -m eval.quality verify --output-dir eval/results/v3_dev_20261019_1003
```

## 기술 스택

| Technology | Role | Why |
| --- | --- | --- |
| Python 3.12 | 앱·파이프라인·평가 실행 환경 | PDF 처리부터 UI까지 한 언어로 구성. 의존성 버전 고정 후 `pip check`로 확인 |
| Streamlit 1.65 | 채팅 UI와 서버 | UI와 서버 코드를 하나의 Python 앱으로 구성해 별도 백엔드·프론트엔드가 필요 없음 |
| Streamlit Community Cloud | 공개 데모 호스팅 | GitHub 저장소에서 바로 배포. API 키는 서버 시크릿에만 보관 |
| PyMuPDF | PDF 텍스트 추출 | 텍스트 기반 PDF를 페이지 단위로 추출해 OCR 없이 정확한 페이지 번호로 인용 |
| LangChain (core, text-splitters, langchain-chroma) | 문서·임베딩 인터페이스, 재귀 분할, Chroma 연동 | 표준 인터페이스로 로컬 임베딩 모델을 Chroma에 연결. 청크 설정은 인덱스 서명에 기록 |
| FastEmbed + ONNX Runtime, `intfloat/multilingual-e5-small` | 문서·질문 임베딩 (384차원) | API 키 없이 CPU에서 로컬 실행, 한국어 지원. Anthropic은 임베딩 API를 제공하지 않음 |
| Chroma | 영구 벡터 인덱스 | 로컬 파일 기반 인덱스. 서명이 같으면 재사용하고 요청 시에만 재생성 |
| Anthropic Claude API (기본 `claude-sonnet-5-5`) | 답변 생성, AI 채점 | 근거 기반 한국어 답변 생성. `ANTHROPIC_MODEL`로 모델 변경 가능 |
| LangSmith | 검색·생성 단계 추적 (선택) | 실행마다 질문·문맥·프롬프트·답변·설정·토큰 사용량 기록. 추적이 실패해도 답변은 막히지 않음 |
| pytest | 자동화 테스트 | 테스트 대역을 사용해 인증 정보·모델 호출 없이 실행 |

## AI 구성 요소

| 단계 | 입력 | 출력 | 처리 주체 |
| --- | --- | --- | --- |
| 임베딩 | 청크 텍스트 또는 질문 | 384차원 벡터 | 로컬 E5 모델 (`passage: ` / `query: ` 접두어) |
| 답변 생성 | 질문 + 검색된 근거 | 답변·답변 가능 여부·주장별 인용문과 출처 ID가 담긴 JSON | Claude, 질문당 최대 1회 호출 |
| AI 채점 (평가 전용) | 답변 + 참고 정답 + 채점 기준 | 판정과 검토 메모 | Claude, 별도 호출 |

**규칙 기반 처리.** PDF 추출, 청크 분할, 유사도 검색, 페이지 문맥 구성(중복 페이지 제거, 페이지 단위로만 포함, 본문을 자르지 않음), 인용문 검증(공백 차이만 무시), 출처 메타데이터. 파일명과 페이지 번호는 모델이 만들지 않습니다.

**모델 선택.** 답변 모델은 `ANTHROPIC_MODEL`, 임베딩 모델은 `EMBEDDING_MODEL`로 지정합니다. 임베딩 모델을 바꾸면 `ingest.py --rebuild`가 필요합니다.

**실패 처리.**
- 근거가 부족하면 출처 없이 정확히 `등록된 문서에서 해당 정보를 확인할 수 없습니다.`를 반환합니다.
- 잘못된 JSON, 존재하지 않는 출처 ID, 근거와 일치하지 않는 인용문은 거부하며 답변을 보여 주지 않습니다.
- Claude 호출은 30초 제한·자동 재시도 없음으로 설정했습니다. 제공업체 오류는 답변 보류와 구분된 예외로 처리하고, 화면에는 안전한 오류 메시지를 표시합니다.
- 평가 실행도 자동으로 재시도하지 않습니다. 실패하거나 건너뛴 기록도 분모에 그대로 포함합니다.

**결과의 성격.** 답변은 합성 문서를 바탕으로 한 참고 정보입니다. 인용문 일치는 주장의 출처를 증명할 뿐 답변이 완전하다는 뜻은 아닙니다. [Phase 5 실패 분석](Phase/Phase5_EvaluationAndDeployment.md)처럼 조건을 빠뜨리는 경우가 있습니다.

## 빠른 시작

### 사전 요구사항

- Python 3.12, Git. 아래 명령은 Windows PowerShell 기준입니다.
- 답변 생성용 Anthropic API 키. 검색·인덱싱에는 키가 필요 없습니다.
- 첫 실행 시 내려받는 임베딩 모델용 디스크 공간 약 487 MB.

### 설치

```powershell
git clone https://github.com/SoyeonAhn3/enterprise-rag.git
Set-Location enterprise-rag
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

### 설정

`.env`에 `ANTHROPIC_API_KEY`를 입력합니다. 나머지는 선택 사항입니다.

| 변수 | 기본값 | 용도 |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | (비어 있음) | 답변 생성에 필수 |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | 답변에 쓰는 Claude 모델 |
| `ANTHROPIC_MAX_TOKENS` | `4096` | 필요한 근거 인용을 포함한 출력 토큰 상한 |
| `RAG_TOP_K` | `3` | 검색할 청크 또는 페이지 수 |
| `RAG_RETRIEVAL_MODE` | `chunks` | `pages`로 바꾸면 페이지 문맥 검색 사용 |
| `RAG_CONTEXT_MAX_CHARS` | `6000` | 페이지 모드의 문맥 글자 수 한도 |
| `EMBEDDING_LOCAL_FILES_ONLY` | `false` | 첫 다운로드 후 `true`로 바꾸면 오프라인으로 모델 로드 |
| `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` | `false`, (비어 있음) | 선택적 추적 |
| `SESSION_QUESTION_LIMIT` | `10` | 세션당 질문 시도 횟수 (실패 포함) |

설정 우선순위: 환경 변수 → Streamlit 시크릿 → `.env` → 기본값. 전체 목록은 [`.env.example`](.env.example)을 참고하세요.

### 실행

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Streamlit이 출력한 로컬 URL을 엽니다. 첫 실행 시 앱이 `deployment/index_bundle.json`의 사전 계산 벡터를 가져오고 질문 임베딩 모델을 내려받으므로 인덱스를 따로 만들 필요가 없습니다. 답변마다 입력한 Claude 키의 API 사용량이 발생합니다.

### 명령행 사용 (선택)

```powershell
# 로컬 인덱스 생성 또는 재사용 (API 키 불필요). PDF·임베딩 모델·청크 설정을 바꾸면 --rebuild 사용
.\.venv\Scripts\python.exe -X utf8 ingest.py
# 검색만 실행 (API 키 불필요)
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# 근거 기반 답변 (Claude 키 사용)
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# 답변 생성 없이 Claude 접속만 확인
.\.venv\Scripts\python.exe -X utf8 llm.py --check
# LangSmith 추적 설정만 확인 (네트워크·모델 호출 없음)
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace --preflight --retrieval-mode pages --top-k 5 --context-max-chars 6000
```

실제 추적 검사, Streamlit Community Cloud 설정, 시크릿, 페이지 모드 활성화는 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

## 테스트

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
# 임베딩·API 호출 없이 청크 분할 미리보기 (data/chunks_preview.json 생성)
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
```

2026-10-19 최신 실행에서 **테스트 488개가 통과**했습니다([테스트 출력](eval/results/citation_completeness_20261019/final/pytest.txt)). 모든 인용 표시·중복 처리·과거 결과 호환성과 기존 파이프라인 검사를 포함합니다. 테스트 대역을 사용하며 실제 모델을 호출하지 않습니다. 프로그램 검증이며 답변 정답률을 뜻하지 않습니다. 별도 오프라인 [화면 재생](eval/results/citation_completeness_20261019/display_check.json)에서는 마지막 답변의 출처 9개·인용 16개가 모두 표시되고 저장된 답변은 바뀌지 않음을 확인했습니다.

새 [v3 평가셋](eval/questions_v3.json)은 개발용 20문항과 최종 평가용 20문항입니다. 최종 묶음은 이제 한 번 실행해 관측한 상태입니다. 각 묶음에는 경계값·복합 조건·예외·기한·답변 불가 질문을 4개씩 포함합니다. 모델 호출 없이 구조·PDF 인용·문구 중복을 검사합니다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m eval.quality validate --dataset eval/questions_v3.json --against eval/questions_v2.json
```

평가기는 데이터셋·묶음과 요청 한도를 고정하며 미채점을 구분합니다. 기존 60문항 답변 보고서도 재현할 수 있습니다. [후속 비교 도구](Phase/Phase6_RetrievalAndAnswerQuality.md#v3-개발-후속-개선--2026-10-19)는 개발용 이전 답변을 재사용하고 전후 답변을 같은 고정 채점기로 평가합니다. v3 개발 개선과 제한한 최종 평가를 기록했고, 남은 실패와 사람 검토 한계는 최신 보고서에 명시했습니다. 과거 선택 재생은 현재 소스 검사가 있으므로 해당 과거 개정은 저장한 [이전 재생 증빙](eval/results/v3_refinement_checks_20261019/retrieval_replay.json)을 참고하세요.

## 프로젝트 구조

```text
Enterprise-rag/
├── app.py                    # Streamlit 채팅 화면 (한국어)
├── app_runtime.py            # 세션 간 공유하는 모델·인덱스·클라이언트 캐시
├── rag.py                    # Retriever와 RAGAssistant. 검색 또는 --answer 명령행
├── retrieval_context.py      # 글자 수 한도 안에서 페이지 문맥 구성
├── grounding.py              # 답변 프롬프트, 엄격한 JSON 파싱, 인용·출처 검증
├── llm.py                    # Claude 클라이언트와 --check 접속 확인
├── ingest.py                 # PDF 추출, 청크 분할, 인덱스 생성·재사용, --rebuild, --dry-run
├── embeddings.py             # 로컬 FastEmbed E5 임베딩
├── index_store.py            # 서명·무결성 검사를 포함한 Chroma 인덱스
├── config.py                 # 설정 로더
├── deployment.py             # 이식 가능한 벡터 번들 내보내기·가져오기·검사
├── tracing.py                # 설정·토큰 사용량을 포함한 선택적 LangSmith 추적
├── source_display.py         # 화면용 출처 발췌 표시
├── documents/                # 실행 시 사용하는 PDF 4개
├── deployment/               # 사전 계산 벡터 번들 (index_bundle.json)
├── eval/                     # 질문셋, 평가 실행기, 추적 검사, AI 채점, 저장된 결과
├── tests/                    # pytest 테스트
├── Phase/                    # Phase 1~6 보고서와 로드맵 (영문 + 국문)
├── plan/                     # MVP 기획서 (국문)
├── rag_mvp_sample_documents/ # 검토한 원본 PDF와 문서 안내
├── docs/evidence/            # 실행 화면 스크린샷
├── .streamlit/               # 테마와 시크릿 템플릿
├── DEPLOYMENT.md             # 배포 안내 (영문 + 국문)
├── .env.example              # 설정 템플릿
├── requirements.txt          # 실행 의존성
└── requirements-dev.txt      # 테스트 의존성
```

인증 정보, 로컬 Chroma DB, 모델 다운로드, 비공개 추적 파일, 생성된 미리보기·검사 결과는 Git에서 제외합니다.

## 현재 상태

| Phase | Status | Deliverable |
| --- | --- | --- |
| [1 — 기반 구축](Phase/Phase1_Foundation.md) | ✅ 완료 | PDF 4개를 페이지 단위로 추출해 출처 메타데이터가 있는 청크 22개 생성 |
| [2 — 인덱싱·검색](Phase/Phase2_IndexingAndRetrieval.md) | ✅ 완료 | 로컬 E5 임베딩, Chroma 영구 인덱스, 재사용·명시적 재생성 |
| [3 — 근거 기반 답변](Phase/Phase3_GroundedAnswers.md) | ✅ 완료 | 질문당 Claude 1회 호출, 인용문 검증, 답변 보류 |
| [4 — Streamlit 화면](Phase/Phase4_StreamlitInterface.md) | ✅ 완료 (로컬) | 출처 표시 채팅, 예시 질문, 안전한 오류 처리, 세션별 제한 |
| [5 — 평가·배포](Phase/Phase5_EvaluationAndDeployment.md) | ✅ 합의한 포트폴리오 범위 완료 | 평가·실패 분석 보존, [공개 데모](https://enterprise-rag-demo-project.streamlit.app/) 배포, 실제 로컬 실행의 LangSmith 원격 대조·사용자 데모 확인 기록. 독립 채점·폭넓은 Cloud 운영 검사는 보류 |
| [6 — 검색·답변 품질](Phase/Phase6_RetrievalAndAnswerQuality.md) | ✅ 합의한 개선 게시 완료 | 테스트 488개; 필수 항목 지침·모든 인용 표시·확인된 인용 누락 보완; 과거 최종 평가 수치는 보존 |

- 코드 기본값은 `chunks`, k=3입니다. 공개 데모는 소유자 보고 기준 Reboot 후 페이지 모드(pages, k=5, 6,000자)로 실행 중이며, 별도로 검증하지는 않았습니다.
- 사용자가 시연 답변 5개를 직접 확인하고 별다른 문제가 없어 보인다고 보고했습니다. 전체 평가 답변과 인용문을 정식 채점한 결과는 아닙니다.
- 이번 개정은 필수 항목 누락 방지 지침, 서로 다른 모든 주장 인용 표시, 인용의 조건·담당자·시점·예상 기간 단서 보존 지침을 포함합니다. 원문 일치 검증은 유지하며 의미적 완전성을 자동으로 보장하지는 않습니다.
- 복합 답변이 기존 2,048토큰 한도에 도달해 기본 출력 상한을 4,096으로 올렸습니다. [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4) 게시 후 사용자가 Cloud `ANTHROPIC_MAX_TOKENS=4096` 설정 완료를 보고했습니다([배포 상태](DEPLOYMENT.md#인용문-출력-한도-2026-10-19)). 최신 게시본의 새 Cloud 질문 실행·재시작은 별도로 관측하지 않았습니다.

## 한계점

- **소규모 합성 문서.** PDF 4개, 13페이지입니다. 실제 기업 문서에서의 성능을 보여 주지 않습니다.
- **개발용 점수의 한계.** 같은 기준의 페이지 비교는 85%→85%이며 참고 정답 오용·추론 판정 불일치가 남았습니다. 일반적인 정확도 개선을 입증하지 않습니다. 이전 60문항 비교의 채점도 미완료입니다.
- **독립 사람 채점 미완료.** 과거 점수는 Claude 채점, 최신 최종 답변은 Codex가 PDF와 대조한 결과입니다. 모두 AI 판정입니다.
- **최종 평가의 제한된 범위.** 같은 문서의 전체 20문항 실행에서 검색 누락 4개·답변 항목 누락 1개·주장 인용 누락 2개를 확인했습니다. 이후 집중 보완에서 관측한 항목·인용 사례를 다뤘지만 원래 20문항 점수를 재계산하지 않습니다. 복합 검색 한계는 남아 있으며, 넓은 의미의 모니터 수령 질문에서 정산 제출 기한을 검색하지 못한 사례도 포함합니다.
- **고정 문서.** 문서 업로드, OCR, 표 인식, 인증, 문서 권한 기능이 없습니다.
- **데모 규모의 서빙.** 공유 잠금으로 요청을 순서대로 처리합니다. 질문 제한은 세션 단위이며 제공업체 전체 예산 통제가 아닙니다. 동시 사용은 검사하지 않았습니다.
- **Cloud 동작 일부만 검증.** 추적은 로컬 실행 기준으로만 검증했고 배포 앱에서는 확인하지 않았습니다. Streamlit Community Cloud에서의 재시작, 시작 시간, 메모리 사용량도 확인하지 않았습니다.

## 향후 계획

현재 완료 범위이며, [개발 현황 및 로드맵](Phase/DevelopmentStatusAndRoadmap.md)에는 이전 평가 이력을 보존합니다.

합의한 포트폴리오 범위는 완료했습니다. 답변 필수 항목·모든 근거 인용 표시·관측한 인용 누락을 보완해 [175bda7](https://github.com/SoyeonAhn3/enterprise-rag/commit/175bda7d923b445c72125bac82ee6820ff9a7dc4)으로 게시했으며, 사용자가 마지막 Cloud 설정 변경 완료를 보고했습니다. 이 범위를 종료하기 위한 추가 개발·새 평가셋·채점기는 필요하지 않습니다. 복합 검색 개선·독립 채점·운영 서비스 검사는 별도 후속 과제로 다룰 수 있습니다.

과거 미완료 채점 87건은 현재 선택 방식이 아닌 이전 답변을 대상으로 합니다. 소스와 채점 프롬프트가 모두 바뀌었으므로 새 계획뿐 아니라 원래 채점기·버전과의 호환도 필요합니다. 기존 계획과 결과는 보존했습니다.

과거 실패한 AI 채점 87건과 기존 사람 검토 34건은 이 제한된 포트폴리오의 종료 조건이 아닙니다. 선택적 후속 작업은 복합 검색 개선, 독립 채점, Cloud 자원 검사, CI, SDK 유지보수입니다. Phase 7 사용성과 동시 접속 검사는 합의한 범위에서 제외합니다.

## 문서

| 문서 | 내용 |
| --- | --- |
| [인용 완전성 검토](eval/results/citation_completeness_20261019/review.json) | 마지막 사례별 판정, 앞선 실패, 실제 호출 수와 남은 한계 |
| [필수 항목·표시 검토](eval/results/completeness_display_20261019/review.json) | 사용자 질문·변형 2개와 인용 보완 전 관찰 결과 |
| [제한한 최종 보고서](eval/results/v3_closeout_20261019/report.md) | 고정한 최종 결과, 실패·시간과 사람 검토용 20문항 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Cloud 설정, 시크릿, 페이지 모드 활성화, LangSmith 검증 (영문 + 국문) |
| [개발 현황 및 로드맵](Phase/DevelopmentStatusAndRoadmap.md) | 최신 점검, 품질 분석, 우선순위별 다음 작업 |
| [Phase 보고서](Phase/) | Phase별 설계·구현·검증 증빙 (영문 + 국문) |
| [MVP 기획서](plan/enterprise_rag_assistant_streamlit_mvp_plan.md) | 요구사항, 아키텍처, 인수 조건 (국문) |
| [샘플 문서 안내](rag_mvp_sample_documents/README.md) | 문서 구성과 근거 대조 규칙 (국문) |
| [60문항 평가 보고서](eval/results/phase5_v2_20261014/report.md) | k=3·k=5 비교, 실패 분석, 검토 목록 (국문) |
| [페이지 문맥 보고서](eval/results/phase6_20261016/report.md) | 검색 비교와 알려진 사례 검사 (국문) |
| [조건 고정 비교 보고서](eval/results/phase6_quality_20261016/report.md) | 60문항 chunks/k=5·pages/k=5 비교, 전체 분모 기준 |

---
<p align="center">Made with AI-assisted development</p>
