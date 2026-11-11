# Enterprise RAG Assistant Architecture

> A RAG demo that retrieves evidence from company policy PDFs, has Claude answer only from that evidence, and shows the answer only when every quote matches the original text

## 1. Overview — What is it made of?

![Overview](overview.svg)

- **Navy boxes**: code that runs for every question and builds the answer. If `grounding.py` cannot verify the citations, no answer reaches the screen.
- **Grouped boxes**: Streamlit app = `app.py` · `app_runtime.py` · `source_display.py`, CLI tools = `ingest.py` · `deployment.py` · `eval/`, Retrieval modules = `index_store.py` · `embeddings.py` · `retrieval_context.py`, Local files = `data/chroma_db` · `data/embedding_models` · `deployment/index_bundle.json` · `eval/results`
- The settings loader `config.py` (`.env` · Streamlit secrets) is read by every module, so it is left out of the diagram to keep the lines readable.

## 2. Workflow — How one question is processed

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
    A(["User question"]) --> B{"Session question<br/>limit left?"}
    B -->|No| X1(["Limit reached notice"])
    B -->|Yes| C{"Question is<br/>1–500 characters?"}
    C -->|No| X2(["Ask to re-enter"])
    C -->|Yes| D["Question count +1"]
    D --> E["Embed question · vector search<br/>top 3 chunks<br/>pages mode: assemble original pages"]
    E --> F{"Any evidence<br/>retrieved?"}
    F -->|None| AB(["Abstention message"])
    F -->|Found| G["Build prompt<br/>question + evidence S1–S3"]
    G --> H["One Claude call<br/>JSON schema response"]
    H --> V{"Citation check<br/>validate_answer"}
    V -->|answerable=false| AB
    V -->|Pass| OK(["Answer + sources shown"])
    V -.->|Rejected| ER(["Error notice<br/>no answer shown"])
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

## 3. Citation Check Flow — How validate_answer decides whether to accept an answer

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
    S(["Claude response string"]) --> M{"Retrieved evidence valid?<br/>S1–S3 order · metadata"}
    M -->|Yes| A{"Response format valid?<br/>≤ 16,000 chars · valid JSON<br/>no duplicate keys · no NaN · exact schema"}
    A -->|Yes| D{"answerable?"}
    D -->|false| E{"claims empty?"}
    E -->|Yes| AB(["Abstention<br/>not found in registered documents"])
    D -->|true| F{"Claims valid?<br/>1–6 claims · text ≤ 1,000 chars<br/>no source markers · 1–3 citations"}
    F -->|Yes| J{"source_id is evidence<br/>actually supplied?"}
    J -->|Yes| K{"Quote is a contiguous passage<br/>of the source? whitespace only"}
    M & A & F & J & K -->|No| X(["AnswerValidationError<br/>answer rejected · no retry"])
    E -->|No| X
    K -->|All citations pass| OK(["Pass<br/>per-claim source tags · original quotes kept"])

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

## 4. Data Flow — What moves in one question

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
    participant U as User
    participant APP as app.py
    participant RAG as rag.py
    participant IX as Retrieval modules
    participant GR as grounding.py
    participant LLM as llm.py
    participant CL as Claude API
    participant LS as LangSmith

    rect rgb(255, 255, 255)
    U->>APP: Question (max 500 chars)
    APP->>APP: validate_question · session limit check
    APP->>RAG: answer(question)<br/>one at a time under RLock
    RAG->>LS: create_run (when tracing is on)
    RAG->>IX: similarity_search_with_score(question, k=3)
    IX->>IX: E5 embedding with query prefix
    IX-->>RAG: 3 chunks<br/>source_file · page · chunk_id · text · distance
    Note over RAG: pages mode assembles original PDF pages (max 6,000 chars)
    RAG->>GR: build_prompt(question, chunks)
    GR-->>RAG: JSON prompt (question · sources S1–S3)
    RAG->>LLM: generate(prompt, SYSTEM_PROMPT, answer_schema)
    LLM->>CL: messages.create<br/>json_schema format · 0 retries
    CL-->>LLM: JSON text + usage
    LLM-->>RAG: Response text (only when stop_reason is end_turn)
    RAG->>GR: validate_answer(raw, chunks)
    alt Check passes
        GR-->>RAG: answer · claims · sources
        RAG->>LS: update_run (stage results · token usage)
        RAG-->>APP: result (answer · sources · latency_ms · trace)
        APP-->>U: Answer + expandable [S1] sources (original quotes)
    else Check rejects
        GR-->>RAG: AnswerValidationError
        RAG->>LS: update_run (validation_error)
        RAG-->>APP: Exception raised
        APP-->>U: Notice that the evidence could not be verified
    end
    end
```
