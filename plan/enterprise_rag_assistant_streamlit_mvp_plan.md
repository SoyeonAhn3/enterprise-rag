# Enterprise RAG Assistant — Streamlit 2일 MVP 개발 기획서

> **2026-10-16 현황·후속 계획:** [개발 현황 및 로드맵](../Phase/DevelopmentStatusAndRoadmap.md), [Phase 5 잔여 작업](../Phase/Phase5_EvaluationAndDeployment.md)을 참고한다. 이 기획서는 초기 요구사항 기준이며 아래 체크리스트는 현재 완료 현황이 아니다. 일부 초기 OpenAI·인덱스 배포 예시는 이후 구현으로 대체되었으므로 현재 실행·배포 절차는 [README_ko.md](../README_ko.md)와 [DEPLOYMENT.md](../DEPLOYMENT.md)를 따른다.

> **문서 유형:** 바이브코딩용 개발 명세서(PRD + 구현 가이드)\
> **작성 기준:** 2026-10-13\
> **기술 선택 갱신:** 2026-10-14 — 사용자 요청으로 Claude API + 로컬 다국어 임베딩으로 전환\
> **목표:** **2일 안에 공개 Live Demo URL, GitHub 소스, 간단한 Eval 결과**를 제출할 수 있는 문서 기반 RAG 웹서비스 완성\
> **배포:** Streamlit Community Cloud (`*.streamlit.app`)\
> **디자인:** Streamlit으로 구현. 상세 색상·레이아웃·브랜딩은 별도 디자인 작업을 통해 조정할 수 있도록 구조 분리

---

## 0. 이번 프로젝트에서 확정한 결정 사항

| 구분 | 최종 선택 |
|---|---|
| 서비스 | Enterprise RAG Assistant — 업무 문서 기반 AI 질의응답 |
| 핵심 시나리오 | 미리 등록된 업무 규정/매뉴얼 PDF를 검색하여 근거 기반 답변 생성 |
| RAG 방식 | **2-Step RAG**: 벡터 검색 1회 → LLM 답변 |
| 웹 UI | **Streamlit** (Python 기반) |
| 배포 | **Streamlit Community Cloud 단일 서비스** |
| 별도 Backend | **없음** (FastAPI·Render 불필요) |
| 별도 Frontend | **없음** (React·Vite·Netlify 불필요) |
| RAG 구현 | Python + LangChain + Chroma |
| 문서 처리 | PyMuPDF + 텍스트 분할 + 페이지 메타데이터 |
| LLM | Anthropic Claude API (`ANTHROPIC_MODEL` 설정으로 모델 변경 가능) |
| Embedding | 로컬 `intfloat/multilingual-e5-small` 384차원, FastEmbed / ONNX Runtime |
| Tracing | LangSmith (실행 추적) |
| Eval | 고정 질문 10개 + Retrieval Hit@3 + 사람의 답변 정답 채점 |
| 사용자 문서 업로드 | **MVP에서 제외**; 문서 3~5개 미리 등록 |
| MCP / LangGraph / 재검색 | **MVP에서 제외** |
| 완료 기준 | 제3자가 Live Demo URL에 접속해 질문, 답변, 실제 출처를 확인할 수 있음 |

### 핵심 원칙

1. **실제로 동작하는 RAG가 우선**이다. 화려한 UI, Agentic RAG, 복잡한 평가 자동화는 하지 않는다.
2. 정확한 근거가 없는 답변은 **모른다고 응답**한다.
3. 답변에 표시하는 **문서명·페이지는 프로그램이 관리한 실제 검색 결과에서만 가져온다.**
4. 사용자는 배포된 앱에 접속하기만 하면 되며, **API 키를 입력하지 않는다.**
5. **LLM API 호출 비용은 앱 운영자에게 발생**하므로 공개 데모에는 비용 보호장치를 적용한다.

---

## 1. 프로젝트 정의

### 1.1 해결하려는 문제

업무 규정, 구매/계약 절차, 시스템 사용 매뉴얼 등이 여러 PDF로 흩어져 있을 때, 사용자는 원하는 항목을 찾기 위해 문서를 열고 검색하고 내용을 정리해야 한다.

### 1.2 제공하는 해결책

사용자가 자연어로 질문하면 문서에서 관련 내용 **상위 3개 Chunk**를 검색하고, LLM이 해당 정보만 참고하여 답변한다. 답변 아래에는 **관련 문서명, 페이지, 짧은 근거 발췌**를 함께 보여준다.

**예시 (실제 문서 내용이 아니라 동작 방식 예시)**

- 질문: `노트북 구매 시 어떤 승인 절차가 필요한가요?`
- 검색: 구매 규정 3페이지, 전결 규정 5페이지 등
- 답변: 실제 문서에서 확인된 절차를 단계별로 설명
- 출처: `구매업무규정.pdf · 3쪽`, `전결규정.pdf · 5쪽`
- 문서에 답이 없으면: `등록된 문서에서 해당 정보를 확인할 수 없습니다.`

### 1.3 대상 사용자

- 회사 매뉴얼을 자주 확인하는 임직원
- 규정·절차 문의를 받는 업무 담당자
- 프로젝트를 평가하는 채용 담당자 또는 포트폴리오 검토자

### 1.4 이번 MVP의 차별점

단순 PDF 챗봇에서 끝내지 않고 다음 결과까지 남긴다.

- **원문 근거와 페이지를 보여주는 답변**
- **근거가 부족할 때 답변 보류**
- **검색·답변 과정을 LangSmith로 추적**
- **10개 테스트 질문에 대한 실제 평가 결과**

---

## 2. 기능 범위

### 2.1 반드시 구현 (Must)

| ID | 기능 | 완료 조건 |
|---|---|---|
| F01 | 미리 등록된 PDF 읽기 | 공개 가능한 텍스트 PDF 3~5개에서 문서 텍스트 추출 |
| F02 | Chunking/Embedding | 문서 조각, 벡터, 출처 메타데이터 생성 |
| F03 | Chroma 검색 | 질문마다 관련 Chunk Top 3 반환 |
| F04 | LLM 답변 | 검색 결과에 근거해 한국어 답변 생성 |
| F05 | 출처 표시 | 파일명, 1부터 시작하는 페이지, 짧은 근거 발췌 제공 |
| F06 | 답변 보류 | 근거 없는 질문에 추측하지 않는 응답 제공 |
| F07 | Streamlit 채팅 UI | 질문 입력, 예시 질문, 답변, 출처, 로딩/오류 상태 |
| F08 | LangSmith Tracing | 검색 단계와 LLM 호출 Trace를 확인 가능 |
| F09 | Mini Eval | 실제 문서 기반 10문항 평가 및 결과 파일 저장 |
| F10 | Live Demo 배포 | Streamlit Community Cloud의 실제 공개 URL로 접속 가능 |

### 2.2 선택 (시간이 남을 때만)

- 앱 화면에 `품질 평가` 탭 추가 (저장된 평가 결과만 읽어서 표시)
- 질문마다 응답 시간 간단 표시
- `st.session_state`를 사용한 현재 세션 채팅 기록 표시
- Streamlit 테마/스타일 수정

### 2.3 이번에는 개발하지 않음 (Out of Scope)

- 파일 업로드로 문서 등록 및 재인덱싱
- 사용자 계정, 역할별 권한, 조직별 문서 관리
- LangGraph, Agentic/Corrective RAG, 질문 재작성 및 재검색
- Hybrid Search, Reranker, Knowledge Graph, MCP
- 문서 자동 요약/보고서 생성, 실시간 외부 웹 검색
- FastAPI, React, Netlify, Render, PostgreSQL, Docker
- LLM-as-a-Judge 자동 채점 플랫폼, 장기 Memory

---

## 3. 문서 데이터 범위

- **텍스트 추출이 가능한 PDF 3~5개**를 하나의 업무 분야에서 선택한다.
- 예: 구매·승인·계약·경비처리 절차의 공개 매뉴얼/규정.
- 스캔 이미지 PDF, OCR, 복잡한 표 인식은 **제외**한다.
- 사용 권한이 있는 문서만 GitHub에 포함한다. **내부 비밀·개인정보가 담긴 회사 문서는 사용하지 않는다.**
- `documents/` 폴더에 문서를 고정해 둔다.
- 문서마다 `source_file`, `page`, `chunk_id`를 보존하며, 페이지는 사용자에게 **1-based**로 표시한다.
- 데모 답변과 평가 질문은 실제로 확보한 문서를 기준으로 작성한다. **문서 내용/정답을 임의로 만들어내지 않는다.**

**데이터 준비 완료 조건**

1. 3~5개 PDF 모두 텍스트 추출 성공.
2. 최소 10개 실제 업무 Q&A가 만들어질 정도의 정보 확보.
3. 최소 2개 문서를 연결해야 답할 수 있는 질문도 준비 가능.

---

## 4. 시스템 아키텍처

```text
┌──────────────────────────────────────────────┐
│ 사용자 브라우저                               │
│ Streamlit Community Cloud (app.py)          │
│                                              │
│ 질문 입력 / 답변 / 근거 / 오류 안내            │
│            │                                 │
│            ▼                                 │
│      RAG 로직 (Python + LangChain)           │
│            │                                 │
│            ├── Chroma (검색 인덱스)           │
│            │       └── Top 3 관련 Chunk     │
│            │                                 │
│            └── LLM API (답변 생성)            │
│                                              │
│            └── LangSmith (Trace)             │
└──────────────────────────────────────────────┘

[오프라인 인덱싱: 개발/배포 전 1회]
PDF 3~5개 → PyMuPDF → Chunking → 로컬 Embedding 모델 → Chroma
```

### 4.1 별도 백엔드가 필요 없는 이유

Streamlit은 Python 코드를 **웹서버에서 직접 실행**하면서 UI를 제공한다. 따라서 이번 MVP의 검색·LLM 호출 코드는 Streamlit 앱 내부의 Python 모듈에서 실행한다.

- 프론트/백엔드 API 계약, CORS, 별도 서버 호스팅이 불필요하다.
- **사용자 브라우저에 OpenAI API 키를 전달하지 않는다.**
- LangChain/Chroma/LLM 호출은 Streamlit 서버 측 Python 코드에서 처리한다.

### 4.2 Chroma 인덱스 운영 전략 (2일 MVP 기준)

**권장: 배포 전에 인덱스를 한 번 생성하고 고정된 데모 인덱스를 앱에서 로드한다.**

1. 로컬에서 `python ingest.py` 실행.
2. `documents/`를 읽고 `data/chroma_db/`에 Chroma 인덱스를 생성.
3. 작은 **공개 데모 전용** 인덱스라면 `data/chroma_db/`를 GitHub에 포함해 배포한다. 업로드 전 용량·문서 사용 허가·민감정보 여부를 반드시 확인한다.
4. Streamlit에서는 `st.cache_resource`를 사용해 인덱스/검색 객체를 한 번만 로드한다.
5. 사용자 질문마다 문서를 다시 파싱하거나 문서 임베딩을 다시 생성하지 않는다.

**예비안:** 배포 플랫폼에서 저장된 인덱스 로딩이 실패할 경우에만 앱 시작 시 최초 1회 인덱스를 빌드하고 `st.cache_resource`로 재사용한다. 이때 서버 재시작/휴면 복귀 후 재빌드되어 초기 대기 및 Embedding API 비용이 발생할 수 있다.

> Community Cloud에서는 런타임 파일 변경을 영구 DB처럼 취급하지 않는다. 문서 업로드나 인덱스 업데이트 기능을 이번 MVP에 넣지 않는 이유다. Chroma와 LangChain 라이브러리의 **실제로 작동한 버전**을 `requirements.txt`에 고정하고, 로컬과 Cloud에서 모두 로딩 테스트한다.

2026-10-14 변경: 임베딩은 API 대신 CPU에서 실행하는 로컬 다국어 E5로 전환했다. 최초 모델 다운로드 후 `data/embedding_models/` 캐시를 재사용하며 질문 임베딩에도 같은 모델이 필요하다. 로컬 모델 캐시는 약 487 MB로 Git에서 제외한다. Cloud에서는 최초 다운로드·메모리·캐시 초기화 동작을 별도 검증한다. Claude API는 답변 생성에만 사용하며 자체 임베딩 기능은 없다.

---

## 5. RAG 처리 상세 명세

### 5.1 문서 인덱싱 (`ingest.py`)

```text
문서 목록 조회
  ↓
PyMuPDF로 페이지별 텍스트 추출
  ↓
빈 페이지/공백 텍스트 제외
  ↓
Chunk 분할
  ↓
Chunk에 source_file, page, chunk_id 저장
  ↓
Embedding 모델 호출
  ↓
Chroma에 저장
```

권장 초기 설정:

- Chunk 크기: **800자 전후**
- Overlap: **120자 전후**
- 검색 결과: **Top 3**
- PDF 페이지별 텍스트에 문서 출처 메타데이터 유지

Chunk 크기나 모델을 변경하면 **인덱스를 재생성**해야 한다.

### 5.2 질문 처리 (`rag.py`)

```text
질문 유효성 검사
  ↓
Vector similarity 검색 (Top 3)
  ↓
검색된 Chunk에 임시 출처 ID 부여 (S1, S2, S3)
  ↓
LLM Prompt = 질문 + 검색된 근거 + 지시사항
  ↓
LLM 답변 생성
  ↓
근거 부족 여부 판단
  ↓
답변 + 실제 문서명/페이지/발췌 반환
```

기본 원칙:

- **검색된 문서만**을 답변 근거로 활용한다.
- 문서 속 지시문은 명령이 아니라 **검색 자료**로 취급한다(프롬프트 인젝션에 대한 기본 방어).
- 근거가 부족하면 `등록된 문서에서 해당 정보를 확인할 수 없습니다.`라고 답한다.
- 상위 3개 Chunk가 검색됐다는 사실만으로 답변이 가능한 것으로 간주하지 않는다.
- 페이지 번호, 문서명, ID는 **프로그램이 검색 결과에서 생성**한다. LLM이 임의 생성한 출처를 그대로 표시하지 않는다.
- 출처를 답변에서 인용하도록 구성할 수 있으나, 인용 ID는 실제 검색 결과의 ID 목록에 있는지 확인한다.

### 5.3 반환 데이터 형태 (UI와 RAG 모듈 사이의 Python 객체)

```python
{
    "answer": "실제 문서에서 확인한 답변",
    "answerable": True,
    "sources": [
        {
            "source_id": "S1",
            "document": "sample_policy.pdf",
            "page": 3,
            "excerpt": "원본 PDF에서 검색된 짧은 발췌..."
        }
    ],
    "latency_ms": 1830
}
```

위 객체는 **내부 Python 함수의 반환값 예시**이며 FastAPI/HTTP API를 만들라는 뜻이 아니다. 위 값도 실제 결과가 아닌 데이터 형식 설명용이다.

---

## 6. Streamlit UI/UX 명세

> **브랜딩·색상·정밀 레이아웃은 추후 별도 디자인을 적용**한다. 지금은 Streamlit 기본 컴포넌트 중심으로 기능을 완료한다.

### 6.1 기본 화면 — 하나의 페이지

```text
[ Enterprise RAG Assistant ]
[등록 문서: 4개]   [문서 기반 답변 안내]

예시 질문: [구매 승인 절차는?] [출장비 기준은?]

----------------------------------------
사용자: 노트북 구매 시 어떤 절차가 필요한가요?

AI: 실제 문서에서 확인된 내용을 단계별로 설명...

참고 문서:
- 구매규정.pdf · 3쪽 (발췌 확인)
- 전결규정.pdf · 5쪽 (발췌 확인)
----------------------------------------

[업무 문서에 대해 질문하세요...]   [전송]
```

### 6.2 Streamlit 컴포넌트

- 제목·서비스 소개: `st.title`, `st.caption`
- 문서 수/사용 안내: `st.sidebar` 또는 상단 컨테이너
- 질문 입력: `st.chat_input`
- 질의응답: `st.chat_message`
- 예시 질문: `st.button`
- 문서 출처/발췌: `st.expander`
- 처리 중: `st.spinner` 또는 상태 표시
- 세션 내 대화 표시: `st.session_state` (저장·로그인 기능 없음)

### 6.3 필수 상태 처리

| 상태 | 동작 |
|---|---|
| 첫 화면 | 서비스 소개 + 예시 질문 + 입력창 |
| 질문 실행 | 로딩 표시, 중복 제출 최소화 |
| 정상 응답 | 답변 + 실제 관련 문서/페이지 |
| 근거 부족 | 모른다는 안내, 출처를 지어내지 않음 |
| 인덱스 없음 | 설정/문서 로딩 오류 안내, 앱 비정상 종료 방지 |
| API 제한·타임아웃 | 친절한 오류 메시지, 가능하면 재시도 유도 |

### 6.4 품질 평가 결과 표시 (선택)

시간이 남으면 `st.tabs(["문서 Q&A", "품질 평가"])`로 **저장된 Eval 결과**를 사용자에게 보여준다. 평가 실행 버튼으로 공개 사용자가 LLM을 반복 호출하도록 만들지는 않는다.

---

## 7. 기술 스택

| 영역 | 기술 | 활용 목적 |
|---|---|---|
| UI + Server | **Streamlit** | 웹화면과 Python 서버를 한 서비스로 구성 |
| 개발 언어 | Python (로컬/배포 동일 버전) | 문서·RAG·평가 실행 |
| RAG | LangChain | 검색·프롬프트·LLM 연계 |
| 문서 파싱 | PyMuPDF | PDF 텍스트 추출·페이지 보존 |
| Text Splitter | langchain-text-splitters | Chunking |
| Embedding | FastEmbed / 로컬 다국어 E5 | 사용자 선택에 따라 API 키 없이 문서/질문 벡터화 |
| Vector DB | Chroma + langchain-chroma | 관련 Chunk 검색 |
| LLM | Anthropic Claude | 사용자 선택에 따른 근거 기반 한국어 답변 |
| Tracing | LangSmith | Retriever/LLM Trace 확인 |
| Eval | Python + JSON | 검색 적중, 응답시간, 수동 정답 검토 |
| 형상관리 | GitHub | 코드, 공개 문서, README |
| 배포 | **Streamlit Community Cloud** | `*.streamlit.app` Live Demo URL |

권장 라이브러리 예시 (`requirements.txt`, 실제 설치 후 버전 고정):

```text
streamlit
langchain
langchain-core
langchain-openai
langchain-chroma
langchain-text-splitters
chromadb
pymupdf
python-dotenv
langsmith
```

> 패키지 버전을 여기서 임의로 고정하지 않는다. **로컬에서 정상 설치·실행된 버전을 `pip freeze` 등을 참고해 정리**한 뒤 배포한다. Python 버전도 Community Cloud 배포 설정에서 로컬과 일치시킨다.

---

## 8. 권장 GitHub 프로젝트 구조

```text
enterprise-rag-assistant/
├── app.py                          # Streamlit 페이지 및 사용자 상호작용
├── rag.py                          # Retriever + LLM + 근거 매핑
├── ingest.py                       # PDF → Chunk → Embedding → Chroma
├── config.py                       # 비밀 설정, 모델명, 검색 옵션
├── documents/                      # 공개 배포 가능한 텍스트 PDF 3~5개
│   └── ...
├── data/
│   └── chroma_db/                  # 배포 전 생성된 인덱스 (공개 데모용일 때만 포함)
├── eval/
│   ├── questions.json              # 10개 검증된 질문 및 정답 근거
│   ├── evaluate.py                 # 검색 평가 및 응답 결과 기록
│   └── results.json                # 실제 측정 후 생성된 결과
├── .streamlit/
│   ├── config.toml                 # 테마 및 앱 동작 설정(선택)
│   └── secrets.toml.example        # 키 이름 예시, 실제 값 금지
├── requirements.txt
├── .gitignore
└── README.md
```

`.gitignore`에 반드시 포함할 항목:

```gitignore
.env
.streamlit/secrets.toml
__pycache__/
.pytest_cache/
*.pyc
```

**주의:** `data/chroma_db`는 공개적으로 허용된 문서에서 만든 인덱스일 때만 저장소에 포함한다. 공개할 수 없다면 앱·저장소를 비공개로 유지하거나 데모용 공개 데이터로 교체한다.

---

## 9. 환경 설정과 API 키 보안

### 9.1 로컬 개발

로컬에서 `ANTHROPIC_API_KEY`를 환경변수 또는 Git에 커밋하지 않는 `.env`로 관리한다. Streamlit 단계에서는 같은 설정 로더에 서버 `st.secrets`를 전달한다. 임베딩에는 API 키가 필요 없다.

`secrets.toml` 형식 **예시(키 값은 가짜 문자열)**:

```toml
ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"
ANTHROPIC_MODEL = "claude-sonnet-5-5"
ANTHROPIC_MAX_TOKENS = 2048
API_TIMEOUT_SECONDS = 30
EMBEDDING_PROVIDER = "fastembed"
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384
EMBEDDING_CACHE_DIR = "data/embedding_models"
EMBEDDING_LOCAL_FILES_ONLY = false
LANGSMITH_TRACING = "true"
LANGSMITH_API_KEY = "YOUR_LANGSMITH_API_KEY"
LANGSMITH_PROJECT = "enterprise-rag-mvp"
```

- **실제 비밀값이 들어간 `secrets.toml`은 GitHub에 올리지 않는다.**
- Python 모듈에서는 Streamlit 서버 내 `st.secrets`를 통해 값을 읽되, 오프라인 `ingest.py`/`evaluate.py`는 동일 설정을 **환경변수 또는 별도 설정 로더로** 읽도록 한다.
- LangSmith 라이브러리가 환경변수를 요구하는 경우, 서버 측에서 안전하게 전달한다. 비밀값을 UI에 출력하거나 로그에 남기지 않는다.
- LangSmith 설정이 없거나 호출 오류가 나더라도 일반적인 RAG 답변은 계속 동작하도록 구성한다.

### 9.2 Streamlit Community Cloud

배포 화면에서 **Advanced settings → Secrets**에 실제 키를 등록한다. 브라우저에 노출되는 Markdown·코드·GitHub에 키를 적지 않는다.

### 9.3 비용·공개 데모 보호

- 질문 최대 길이 (예: 500자), 모델의 출력 토큰 한도, API 타임아웃을 설정한다.
- `st.session_state` 기반 연속 질문 수 제한을 **간이 데모 보호**로 둘 수 있다. 단, 세션 초기화로 우회될 수 있으므로 강력한 rate-limit가 아니다.
- API 제공업체의 **프로젝트 사용량 한도 및 예산 알림**을 사용한다. 공개 URL을 공유할 때는 비용 발생에 주의한다.
- 문서 원문과 사용자 질문이 외부 LLM/Tracing 서비스로 전달될 수 있으므로 **공개 가능한 데모 문서만** 사용한다.

---

## 10. Mini Eval + Tracing 요구사항

### 10.1 평가 데이터: 10문항

| 질문 유형 | 수량 | 평가 포인트 |
|---|---:|---|
| 단일 문서에서 정답 확인 | 6 | 검색이 필요한 페이지를 찾는가 |
| 두 문서를 함께 확인 | 2 | 여러 문서의 근거를 찾아 답하는가 |
| 문서에 답이 없는 질문 | 2 | 없는 내용을 만들어내지 않는가 |
| **합계** | **10** | |

평가셋 원본은 `rag_mvp_sample_documents/eval/questions.json`에 있으며, 앱 구현 시 프로젝트의 `eval/questions.json`으로 사용한다. 평가 질문·정답·근거 발췌는 색인하거나 RAG 답변 생성에 제공하지 않는다.

`evidence_groups`는 답변에 필요한 정보별 필수 그룹이며 그룹 사이는 **AND**, 각 그룹의 `any_of` 후보 사이는 **OR**다. `claim`은 확인할 사실이고 후보의 `quote`는 원문 발췌다. 다음은 확정된 합성 문서 평가셋의 **구조 예시**다:

```json
[
  {
    "id": "q03",
    "question": "업무용 장비가 납품되면 요청 부서는 언제까지 검수를 등록해야 하나요?",
    "expected_answer": "납품 또는 수령 후 3영업일 이내에 검수 결과를 등록해야 합니다.",
    "evidence_groups": [
      {
        "id": "inspection_deadline",
        "claim": "요청 부서는 납품 또는 수령 후 3영업일 이내에 검수 결과를 등록한다.",
        "any_of": [
          {
            "document": "04_contract_settlement.pdf",
            "page": 2,
            "quote": "물품은 납품일, 용역은 계약상 산출물 제출일을 기준으로 요청 부서가 3영업일 이내 검수 결과를 등록한다."
          },
          {
            "document": "01_purchase_process.pdf",
            "page": 3,
            "quote": "제품 또는 서비스가 제공되면 요청 부서는 납품·완료 사실을 확인하고, 수령 후 3영업일 이내에 검수 결과를 등록한다."
          }
        ]
      }
    ],
    "answerable": true,
    "category": "single_document",
    "answer_keywords": ["3영업일", "검수"],
    "grading_criteria": ["납품 또는 수령 후 3영업일 이내 검수 등록으로 답하고 다른 업무 기한과 혼동하지 않는다."]
  },
  {
    "id": "q10",
    "question": "가온비즈 해외 출장 시 일본 숙박비 1박 상한은 얼마인가요?",
    "expected_answer": "등록된 문서에는 해외 출장 숙박비 상한에 대한 정보가 없습니다.",
    "evidence_groups": [],
    "answerable": false,
    "category": "unanswerable",
    "answer_keywords": [],
    "grading_criteria": ["등록된 문서에서 확인할 수 없다고 보류하며 숙박비 금액을 추정하지 않는다."]
  }
]
```

### 10.2 평가 방식

- **Retrieval Hit@3 (페이지 적중):** 정답이 존재하는 8문제에서, 검색 결과 상위 3개에 `evidence_groups`의 후보 근거(문서 + 페이지)가 **최소 1개** 들어간 비율. 대체 후보 중 어느 것을 찾아도 인정하며, 같은 페이지의 여러 후보가 적중해도 질문당 한 번만 집계한다.
- **Multi-document Coverage:** 다중 문서 질문 2개에서 **모든 필수 그룹마다 후보 페이지가 하나 이상** Top 3에 포함됐는지 별도 체크한다. 그룹 내 대체 후보 전부를 요구하지 않는다. q07은 결재권자와 보안검토, q08은 결재권자와 법무 검토 근거를 각각 확보해야 한다.
- **실제 근거 확인:** 페이지 적중만으로 정답 문장을 확보했다고 간주하지 않는다. 후보의 `quote`를 참고해 검색된 Chunk에 필요한 근거가 포함됐는지 사람이 확인한다. PDF 추출 시 줄바꿈·공백 차이는 정규화할 수 있다.
- **Answer Correctness:** 10개 최종 답변을 사람이 실제 문서와 `grading_criteria`에 따라 맞음/틀림으로 평가하고, 핵심 주장이 실제 검색 근거로 뒷받침되는지도 확인한다. `expected_answer`는 참고 설명이며 문장 전체 일치를 요구하지 않는다. `answer_keywords`는 보조 정보이고 자동 정답 판정에 사용하지 않는다. 수동 채점임을 결과에 명시한다.
- **Abstention:** 답이 없는 2문제 중 적절하게 답변을 보류한 비율.
- **Latency:** 10개 질문에 대한 응답 시간 평균.

`answerable: false`인 질문은 검색 적중률과 다중 문서 Coverage에서 제외한다. 빈 `evidence_groups`를 근거 확보 성공으로 처리하지 않는다. 검색 평가에는 답변에 인용된 출처만이 아니라 **원래 검색된 Top 3 전체**를 사용한다.

실행 절차:

1. `python -m eval.evaluate` (필요하면 `eval/__init__.py` 추가) 실행.
2. 10문제를 순차 질문하여 **검색 결과 및 LLM 응답, 응답시간** 저장.
3. 자동 계산 가능한 Hit@3/Latency 출력.
4. 사람이 Answer Correctness를 검토하고 `eval/results.json`에 수동 채점 결과 기록.
5. README에 **실제 결과**와 실패한 사례 1개, 개선 방향을 정리.

> 목표 정확도나 개선 퍼센트를 임의로 만든 뒤 실측 결과처럼 기록하지 않는다. 결과가 낮더라도 정직한 결과와 실패 분석이 포트폴리오에 더 의미 있다.

### 10.3 LangSmith Tracing

최소한 다음 단계가 Trace에서 구분돼야 한다.

```text
사용자 질문
  → Retriever: 검색 문서/Chunk
  → LLM: 입력·출력 및 시간
  → 최종 답변
```

- 실제 실행 Trace가 생성되는지 최소 1회 확인한다.
- API Key·개인정보·비공개 원문이 외부 Trace에 포함되지 않게 한다.
- **별도의 자체 Tracing Dashboard는 만들지 않는다.**
- 제출물에는 Trace 화면 캡처를 포함할 수 있다.

---

## 11. 2일 개발 계획

### Day 1 — 로컬 동작 완성

- [ ] 공개 가능한 텍스트 PDF 3~5개 준비 및 추출 확인
- [ ] `ingest.py` 구현: Chunking + Embedding + Chroma
- [ ] `rag.py` 구현: Top 3 검색 + LLM 답변
- [ ] 답변 보류 규칙 및 문서명·페이지 매핑
- [ ] `app.py` 구현: Streamlit 채팅 UI + 출처 Expander
- [ ] 실제로 답이 있는 질문 2개, 없는 질문 1개 테스트

**Day 1 완료 정의:** `streamlit run app.py`에서 질문 → 답변 → 출처가 끝까지 정상 작동한다.

### Day 2 — 평가·추적·배포

- [ ] 실제 문서 기준 Eval 질문 10개 작성
- [ ] Retrieval Hit@3 + 응답시간 자동 계산
- [ ] 답변 10개 수동 확인 및 결과 기록
- [ ] LangSmith Tracing 연동, 검색/LLM Trace 1건 이상 확인
- [ ] GitHub `requirements.txt`, 보안 설정, README 정리
- [ ] Streamlit Community Cloud 배포 및 Secrets 등록
- [ ] 시크릿 모드에서 공개 URL 접속, 질문 3개 테스트
- [ ] README에 Live Demo URL, 평가 결과, 구조, 스크린샷 반영

**Day 2 완료 정의:** 다른 사람이 공개 URL로 접속해 문서 기반 답변과 출처를 확인할 수 있고, 개발자는 Eval 결과와 Trace를 제시할 수 있다.

### 일정이 밀릴 때 우선순위

`기본 RAG 정상 작동 > 출처 표시 > 공개 URL > 최소 Eval > LangSmith Tracing > 디자인 꾸미기`

최종 제출에 반드시 필요한 것은 **동작하는 공개 URL과 실제 출처가 있는 답변**이다. 다른 기능이 불완전해도 README에 구현 여부를 사실대로 적는다.

---

## 12. 로컬 실행 및 배포 절차

### 12.1 로컬 실행

```bash
# 프로젝트 루트에서
python -m venv .venv

# 가상환경 활성화 (OS별 명령 사용)
pip install -r requirements.txt

# 문서 인덱스 생성 (로컬 비밀키 설정 필요)
python ingest.py

# 웹앱 실행
streamlit run app.py
```

- `documents/`에 실제 PDF를 넣었는지 확인.
- `data/chroma_db/`가 정상 생성됐는지 확인.
- 로컬에서 **문서에 있는 질문/없는 질문**을 모두 테스트.
- 질문마다 `ingest.py`가 재실행되지 않아야 한다.

### 12.2 GitHub 업로드

- 프로젝트 루트에 `app.py`, `requirements.txt`, `README.md`가 있어야 한다.
- 사용 권한 있는 공개 데모 문서와 작은 인덱스만 업로드.
- 실제 `.streamlit/secrets.toml`, `.env`, 기타 키 파일은 업로드 금지.
- 의존성 버전과 Python 버전을 로컬에서 확정.

### 12.3 Streamlit Community Cloud 배포

1. [https://share.streamlit.io/](https://share.streamlit.io/)에서 로그인하고 GitHub 저장소 연결.
2. `Create app`에서 Repository/Branch 선택.
3. Entrypoint를 **`app.py`**로 지정.
4. **Advanced settings**에서 로컬에서 사용한 Python 버전 선택.
5. **Secrets**에 `OPENAI_API_KEY`, LangSmith 설정값 등을 등록.
6. 배포 후 `https://<선택한-서브도메인>.streamlit.app` 형태의 Live Demo URL 확인.
7. 인덱스 로딩과 정상 질문/근거 부족 질문을 모두 확인.
8. 배포 URL을 README와 제출 서류에 기재.

### 12.4 배포 시 주의사항

- Community Cloud 앱은 **12시간 동안 방문이 없으면 휴면 상태**로 전환될 수 있다. 새 방문자가 앱을 깨울 수 있으므로 제출 직전 접속 테스트를 한다.
- `requirements.txt` 누락 또는 Python 버전 차이는 대표적인 배포 실패 원인이다.
- 런타임 파일에 의존해 영구 데이터 저장을 구현하지 않는다.
- Cloud 앱이 재시작해도 **고정 데모 인덱스를 다시 로드할 수 있어야** 한다.
- 원격 API 장애 시 오류를 숨기거나 가짜 답변을 출력하지 않는다.

---

## 13. 테스트/인수 조건 (Definition of Done)

### RAG

- [ ] PDF 3~5개에서 검색 가능한 텍스트를 추출함.
- [ ] 문서 단위뿐 아니라 **페이지 단위 메타데이터**가 유지됨.
- [ ] 질문에 대해 Chroma Top 3 검색이 수행됨.
- [ ] LLM 답변이 검색된 자료를 근거로 작성됨.
- [ ] 답변 아래에 **실제 문서명과 페이지**가 표시됨.
- [ ] 문서에 없는 질문에서 임의 사실을 만들지 않고 보류함.

### Web

- [ ] Streamlit에서 질문 입력/답변/출처 확인 가능.
- [ ] 로딩 및 오류 메시지가 구현됨.
- [ ] 공개 Streamlit URL을 시크릿 모드로 접속 가능.
- [ ] 외부 검토자에게 API 키 입력을 요구하지 않음.

### Quality

- [ ] 10개 실제 문서 기반 평가 질문이 있음.
- [ ] Hit@3 및 Latency 실제 결과를 확인 가능.
- [ ] 사람에 의한 답변 정확도 평가가 기록돼 있음.
- [ ] LangSmith에서 실제 Trace 1건 이상 확인 가능.

### Submission

- [ ] GitHub README에 목적/기능/아키텍처/실행법이 정리됨.
- [ ] Live Demo URL이 포함됨.
- [ ] 실제 Eval 결과와 제한 사항이 적혀 있음.
- [ ] 비밀키가 GitHub 저장소와 화면에 노출되지 않음.

---

## 14. README 및 포트폴리오 구성

README 권장 순서:

1. **프로젝트 소개:** 업무 PDF 기반 근거 검색 AI 서비스
2. **Live Demo:** 실제 Streamlit URL
3. **핵심 기능:** 문서 검색 / LLM 답변 / 출처 표시 / 근거 부족 시 보류
4. **아키텍처:** PDF → Chunk → Embedding → Chroma → Retriever → LLM
5. **기술 스택:** Python, Streamlit, LangChain, Chroma, OpenAI, LangSmith
6. **실행 방법:** 설치, 비밀키 설정, 인덱싱, 앱 실행
7. **Eval 결과:** 10문항 실측 결과, 잘 된/실패한 사례
8. **Tracing:** 실제 Trace 화면 캡처
9. **한계:** 소규모 고정 문서, 단일 검색, 권한 관리 없음

포트폴리오 설명 예시 (실제 구현 및 측정한 내용으로 수정):

> **LangChain·Chroma 기반 문서 검색 RAG 웹앱을 Streamlit으로 구현하고 Community Cloud에 배포했습니다. PDF 페이지 메타데이터를 활용한 출처 표시 및 근거 부족 시 답변 보류 기능을 개발했으며, 10개 QA 평가셋과 LangSmith Tracing으로 검색·생성 과정을 점검했습니다.**

---

## 15. 바이브코딩 개발 지침 — 코딩 Agent에 그대로 전달 가능

### 최상위 구현 지시

> 이 문서를 단일 소스 오브 트루스(개발 요구사항)로 삼아 **2일 MVP 범위만** 구현한다. `Python + Streamlit + LangChain + Chroma`로 동작하는 업무 문서 RAG를 만든다. **React, FastAPI, Netlify, Render, LangGraph, MCP 등 제외된 기능을 임의로 추가하지 않는다.** 웹 디자인은 Streamlit 기본 컴포넌트로 우선 구현하며 향후 테마 변경이 가능하게 작성한다. 모든 문서 답변에 실제 출처를 표시하고, 답할 근거가 없다면 보류한다. 비밀키는 안전하게 관리한다. 주요 함수는 UI와 분리한다.

### 단계별 코딩 요청

**Prompt 1 — RAG 데이터 준비**

> `documents/`에 있는 텍스트 PDF를 PyMuPDF로 읽고 페이지별 메타데이터를 보존해 Chunk로 나눈 뒤, OpenAI Embeddings와 Chroma로 저장하는 `ingest.py`를 구현해줘. 로컬에서 단독 실행할 수 있게 하고, 생성된 문서/Chunk 수를 출력해줘. API 키를 코드에 하드코딩하지 마.

**Prompt 2 — RAG 질의응답**

> 생성된 Chroma 인덱스를 로드해 질문과 유사한 Chunk Top 3를 검색하고, LLM에 근거로 제공하여 한국어 답변을 생성하는 `rag.py`를 작성해줘. 실제 문서명·페이지를 출처로 반환하고, 근거 부족 시 답변을 보류하도록 해줘. LLM이 만들어낸 가짜 출처가 출력되지 않게 검증해줘.

**Prompt 3 — Streamlit UI**

> `app.py`에 Streamlit 채팅 인터페이스를 구현해줘. 예시 질문, 질문 입력, 로딩, 답변, 출처 발췌 expander, 오류 처리만 포함해줘. RAG 계산 로직은 `rag.py`에 두고 Streamlit에서 호출하게 해줘. React/FastAPI/별도 API 서버는 사용하지 마.

**Prompt 4 — Eval/Tracing**

> 실제 등록된 PDF를 기반으로 10문항을 작성하고, `eval/evaluate.py`에서 Retrieval Hit@3와 응답시간을 계산하고 답변을 저장하게 해줘. 정답을 문서에서 검증하고 답변 정확도는 수동 채점하도록 구성해줘. LangSmith Tracing을 연결하고 Trace 확인 방법을 README에 설명해줘.

**Prompt 5 — 배포/검증**

> `requirements.txt`, `.gitignore`, `README.md`, `.streamlit/secrets.toml.example`를 정리하고 Streamlit Community Cloud에서 `app.py`를 바로 배포할 수 있게 해줘. 배포 시 로컬 인덱스가 로드되는지, API 키가 노출되지 않는지, 답변/출처/보류/오류 처리가 정상인지 점검해줘.

### 코딩 Agent 작업 원칙

- 한 번에 모든 단계를 구현하지 말고 **각 단계가 동작하는지 확인한 후 다음 단계**로 넘어간다.
- API·버전 관련 오류는 설치된 라이브러리의 실제 인터페이스에 맞춰 수정한다.
- 사양에 없는 기능으로 프로젝트를 확장하지 않는다.
- 임의의 테스트 정답, 성능 수치, Live Demo URL을 만들어내지 않는다.
- 오류가 해결되지 않으면 원인·현재 영향·우회 방안을 README에 사실대로 남긴다.

---

## 16. 공식 참고 자료

- Streamlit Community Cloud 배포: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy
- Streamlit 의존성 파일: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies
- Streamlit Secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management
- Streamlit 캐싱: https://docs.streamlit.io/develop/concepts/architecture/caching
- Streamlit 앱 관리·휴면: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app
- LangChain 문서: https://docs.langchain.com/
- LangSmith 문서: https://docs.smith.langchain.com/

---

## 최종 한 줄 요약

**2일 안에 Streamlit Community Cloud로 공개 가능한 RAG 웹앱을 만들고, 근거 기반 답변·문서 출처·10문항 Mini Eval·LangSmith Tracing까지 구현하여 실제 동작하는 AI Engineering 포트폴리오를 완성한다.**
