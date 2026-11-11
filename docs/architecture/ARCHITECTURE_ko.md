# Enterprise RAG Assistant 아키텍처

> 회사 규정 PDF에서 근거를 검색하고, Claude가 그 근거로만 답하게 한 뒤, 인용문이 실제 원문과 일치할 때만 답변을 보여 주는 RAG 데모

## 1. 구성도 — 무엇으로 이루어져 있나

![구성도](overview_ko.svg)

- **네이비 박스**: 질문마다 실행되어 답변을 만드는 코드. `grounding.py`가 인용을 검증하지 못하면 답변을 화면에 내보내지 않습니다.
- **묶은 박스**: Streamlit 앱 = `app.py` · `app_runtime.py` · `source_display.py`, 명령줄 도구 = `ingest.py` · `deployment.py` · `eval/`, 검색 모듈 = `index_store.py` · `embeddings.py` · `retrieval_context.py`, 로컬 파일 = `data/chroma_db` · `data/embedding_models` · `deployment/index_bundle.json` · `eval/results`
- 모든 모듈이 읽는 설정 로더 `config.py`(`.env` · Streamlit secrets)는 선이 너무 많아져 그림에서 뺐습니다.

## 2. 작업 흐름 — 질문 하나가 처리되는 순서

```mermaid
---
config:
  theme: base
  fontFamily: "Segoe UI, Malgun Gothic, sans-serif"
  flowchart:
    curve: basis
    nodeSpacing: 30
    rankSpacing: 36
    padding: 10
    wrappingWidth: 400
  themeVariables:
    fontSize: 14px
    primaryColor: "#FFFFFF"
    primaryTextColor: "#1F2937"
    primaryBorderColor: "#94A3B8"
    lineColor: "#64748B"
    edgeLabelBackground: "#FFFFFF"
---
flowchart TD
    A(["사용자 질문"]) --> B{"세션 질문 한도<br/>남음?"}
    B -->|아니오| X1(["한도 도달 안내"])
    B -->|예| C{"1~500자 질문?"}
    C -->|아니오| X2(["다시 입력 안내"])
    C -->|예| D["질문 횟수 +1"]
    D --> E["질문 임베딩 · 벡터 검색<br/>상위 3개 청크<br/>pages 모드면 원본 페이지 조립"]
    E --> F{"검색된 근거<br/>있음?"}
    F -->|없음| AB(["답변 보류 문구"])
    F -->|있음| G["프롬프트 생성<br/>질문 + 근거 S1~S3"]
    G --> H["Claude 호출 1회<br/>JSON 스키마 응답"]
    H --> V{"인용 검증<br/>validate_answer"}
    V -->|answerable=false| AB
    V -->|통과| OK(["답변 + 출처 표시"])
    V -.->|거부| ER(["오류 안내<br/>답변 표시 안 함"])
    H -.->|ClaudeError| ER

    classDef actor fill:#334155,stroke:#334155,color:#FFFFFF
    classDef core fill:#1E3A5F,stroke:#1E3A5F,color:#FFFFFF
    classDef decision fill:#FFFFFF,stroke:#1E3A5F,stroke-width:1.5px,color:#1E3A5F
    classDef neutral fill:#F1F5F9,stroke:#94A3B8,color:#334155
    class A actor
    class OK core
    class B,C,F,V decision
    class X1,X2,AB,ER neutral
    linkStyle default stroke:#64748B,stroke-width:1.3px
```

## 3. 인용 검증 흐름 — validate_answer가 답변을 받아들일지 결정하는 방법

```mermaid
---
config:
  theme: base
  fontFamily: "Segoe UI, Malgun Gothic, sans-serif"
  flowchart:
    curve: basis
    nodeSpacing: 30
    rankSpacing: 36
    padding: 10
    wrappingWidth: 400
  themeVariables:
    fontSize: 14px
    primaryColor: "#FFFFFF"
    primaryTextColor: "#1F2937"
    primaryBorderColor: "#94A3B8"
    lineColor: "#64748B"
    edgeLabelBackground: "#FFFFFF"
---
flowchart TD
    S(["Claude 응답 문자열"]) --> M{"검색 근거 형식 정상?<br/>S1~S3 순서 · 메타데이터"}
    M -->|예| A{"응답 형식 정상?<br/>16,000자 이하 · 유효한 JSON<br/>중복 키 · NaN 없음 · 스키마 일치"}
    A -->|예| D{"answerable?"}
    D -->|false| E{"claims가 비었나?"}
    E -->|예| AB(["답변 보류<br/>등록된 문서에서 확인 불가"])
    D -->|true| F{"claim 형식 정상?<br/>1~6개 · text 1,000자 이하<br/>출처 표기 없음 · 인용 1~3개"}
    F -->|예| J{"source_id가<br/>실제 전달한 근거?"}
    J -->|예| K{"quote가 원문 연속 구간?<br/>공백 차이만 허용"}
    M & A & F & J & K -->|아니오| X(["AnswerValidationError<br/>답변 거부 · 재시도 없음"])
    E -->|아니오| X
    K -->|모든 인용 통과| OK(["통과<br/>claim별 출처 표시 · 원문 인용 보관"])

    classDef actor fill:#334155,stroke:#334155,color:#FFFFFF
    classDef decision fill:#FFFFFF,stroke:#1E3A5F,stroke-width:1.5px,color:#1E3A5F
    classDef neutral fill:#F1F5F9,stroke:#94A3B8,color:#334155
    classDef pass fill:#E7EFEA,stroke:#4F7A5E,color:#2F4F3A
    classDef stop fill:#F3E6E6,stroke:#8B3A3A,color:#6B2C2C
    class S actor
    class M,A,D,E,F,J,K decision
    class AB neutral
    class OK pass
    class X stop
    linkStyle default stroke:#64748B,stroke-width:1.3px
```

## 4. 데이터 흐름 — 질문 한 번에 무엇이 오가나

```mermaid
---
config:
  theme: base
  fontFamily: "Segoe UI, Malgun Gothic, sans-serif"
  sequence:
    mirrorActors: false
    messageAlign: left
    actorMargin: 60
  themeVariables:
    fontSize: 14px
    actorBkg: "#1E3A5F"
    actorBorder: "#1E3A5F"
    actorTextColor: "#FFFFFF"
    actorLineColor: "#CBD5E1"
    signalColor: "#475569"
    signalTextColor: "#1F2937"
    noteBkgColor: "#F1F5F9"
    noteBorderColor: "#CBD5E1"
    noteTextColor: "#334155"
    labelBoxBkgColor: "#F8FAFC"
    labelBoxBorderColor: "#94A3B8"
    labelTextColor: "#1E3A5F"
    loopTextColor: "#334155"
    sequenceNumberColor: "#FFFFFF"
---
sequenceDiagram
    autonumber
    participant U as 사용자
    participant APP as app.py
    participant RAG as rag.py
    participant IX as 검색 모듈
    participant GR as grounding.py
    participant LLM as llm.py
    participant CL as Claude API
    participant LS as LangSmith

    rect rgb(255, 255, 255)
    U->>APP: 질문 (최대 500자)
    APP->>APP: validate_question · 세션 한도 확인
    APP->>RAG: answer(question)<br/>RLock으로 한 번에 하나씩
    RAG->>LS: create_run (추적이 켜진 경우)
    RAG->>IX: similarity_search_with_score(question, k=3)
    IX->>IX: query 접두어를 붙여 E5 임베딩
    IX-->>RAG: 청크 3개<br/>source_file · page · chunk_id · text · distance
    Note over RAG: pages 모드면 원본 PDF 페이지로 근거 조립 (최대 6,000자)
    RAG->>GR: build_prompt(question, chunks)
    GR-->>RAG: JSON 프롬프트 (question · sources S1~S3)
    RAG->>LLM: generate(prompt, SYSTEM_PROMPT, answer_schema)
    LLM->>CL: messages.create<br/>json_schema 형식 · 재시도 0회
    CL-->>LLM: JSON 텍스트 + usage
    LLM-->>RAG: 응답 텍스트 (stop_reason이 end_turn일 때만)
    RAG->>GR: validate_answer(raw, chunks)
    alt 검증 통과
        GR-->>RAG: answer · claims · sources
        RAG->>LS: update_run (단계 결과 · 토큰 사용량)
        RAG-->>APP: result (answer · sources · latency_ms · trace)
        APP-->>U: 답변 + [S1] 출처 펼침 (인용 원문)
    else 검증 거부
        GR-->>RAG: AnswerValidationError
        RAG->>LS: update_run (validation_error)
        RAG-->>APP: 예외 전달
        APP-->>U: 근거를 검증하지 못했다는 안내
    end
    end
```
