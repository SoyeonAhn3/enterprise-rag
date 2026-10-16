[English](README.md) | [한국어](README_ko.md)

# Enterprise RAG Assistant

업무 규정에 관한 질문에 검색 증강 생성(RAG)으로 답하는 포트폴리오 프로젝트입니다. Streamlit 앱은 고정 PDF에서 근거를 검색하고 한국어 답변과 함께 문서명·페이지·발췌를 보여 줍니다.

2일 MVP 기획의 범위 안에서 공개 Streamlit 데모, 소스 코드, 실제 측정한 평가 결과를 제공하는 것이 목표입니다.

## 검증 성과

**2026-10-14 기존 답변 평가**는 **합성 한국어 PDF 4개, 13페이지, 청크 22개, 질문 10개**를 대상으로 했습니다. 자동 검사는 **2026-10-16**에 다시 실행했습니다.

| 평가 항목 | 기록된 결과 | 확인한 내용 |
| --- | --- | --- |
| 검색 Hit@3 | **8/8 (100%)** | 답이 있는 각 질문에서 상위 3개 청크에 허용된 근거 페이지가 하나 이상 포함됨 |
| 다중 문서 페이지 Coverage | **2/2** | 검색 결과에 모든 필수 근거 그룹의 허용된 페이지가 포함됨 |
| 답변 불가 질문 보류 | **2/2** | 문서에 답이 없는 질문에 답변을 보류함 |
| AI 에이전트 검토 정답 | **9/10 (90%)** | 참고 정답과 채점 기준에 따른 판정이며, 올바른 답변 보류 2건을 포함함 |
| 평균 RAG 응답 시간 | **3.33초** | 검색·답변 생성 시간이며 모델·인덱스·클라이언트 초기화는 제외함 |
| 자동화 테스트 | **243개 통과** | 2026-10-16 프로그램 동작·실패 처리 검사이며, 답변 평가와는 별개임 |

정답 여부는 AI 에이전트가 검토했으며 **사람 채점은 아직 완료되지 않았습니다**. 답이 있는 질문만 보면 **7/8 (87.5%)**입니다. 이 수치는 소규모 합성 평가셋의 결과입니다. q08은 결론에 근거가 있었지만 필수 설명이 누락되었으며, [실패 분석](Phase/Phase5_EvaluationAndDeployment.md)에 해당 한계를 기록했습니다.

근거는 [기존 평가 실행 원본](eval/results/phase5_baseline.json), [기존 집계 지표](eval/results/phase5_metrics.json), [AI 검토 기록](eval/results/phase5_agent_review.json), [테스트 243개 검증 기록](eval/results/phase5_v2_20261014/verification_20261016.json)에서 확인할 수 있습니다.

확대 평가도 2026-10-14에 완료했으며 **질문 60개·답변 120개·AI 채점 120개**를 저장했습니다. 개발용 검색만으로 B(800자/중복120자/k=5)를 선택하여 A(800/120/3)와 비교했습니다. 앱 기본값은 k=3을 유지합니다.

| 구분 | A AI 정답 | B AI 정답 |
| --- | --- | --- |
| 개발용 40문항 | 35/40 (87.5%) | 39/40 (97.5%) |
| 최종 확인용 20문항 | 13/20 (65.0%) | 15/20 (75.0%) |

생성과 채점은 같은 Claude 모델의 별도 호출이며 사람 검토는 대기 중입니다. [확대 보고서](eval/results/phase5_v2_20261014/report.md)에 실패 분석·중간 저장 복구·검토 목록 34건을 기록했습니다. 2026-10-15 오프라인 검증에서 저장 산출물의 지표를 재현했습니다. 보고서는 실패·누락을 표시하고 성공 응답이 없는 실행도 처리하며 검토 CSV의 사람 메모를 보호합니다.

```powershell
# 읽기 전용 검증. 모델 호출·인증 정보 불필요.
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
```

## 현재 상태

**Phase 1~4는 로컬 동작을 검증했습니다. Phase 5의 평가·추적 연동·배포 준비를 구현했으며 공개 배포와 실제 LangSmith 검증은 대기 중입니다.**

[2026-10-16 개발 현황 및 로드맵](Phase/DevelopmentStatusAndRoadmap.md)에 코드·검증 근거와 남은 작업을 연결했습니다. 공개 배포·추적 완료 → 검색 품질 개선 → 선택적 사용성·기업용 확장 순서입니다. 이번 점검에서 새 모델 호출 없이 테스트 243개, 저장 지표 재현, 배포 번들 검증을 통과했습니다.

| 현재 준비된 자료 | 내용 |
| --- | --- |
| MVP 기획서 | 요구사항, 아키텍처, 구현 순서, 인수 조건 |
| 샘플 문서 | 한국어 PDF 4개, 총 13페이지 |
| 평가 데이터셋 | 기존 10문항과 개발용·최종 확인용을 분리한 60문항 v2 |
| 오프라인 전처리 | PDF 4개·13페이지에서 출처 메타데이터를 포함한 청크 22개 생성 |
| 인덱싱·검색 | Chroma 영구 저장, 호환 인덱스 재사용, 명시적 재생성, 상위 3개 검색 |
| 로컬 검증 | 테스트 243개 통과. 산출물 연결·실패 및 누락 보고·사람 CSV 보존과 기존 RAG·화면·배포 검사 포함 |
| 실제 모델 검색 | 로컬 E5 모델로 q01·q07·q08의 필수 근거 그룹과 원문 발췌를 모두 확보 |
| 근거 기반 답변 | `RAGAssistant.answer()`가 검색 1회·최대 Claude 호출 1회로 주장·인용·전체 검색 결과·시간 반환 |
| 실제 Claude 검사 | q01·q07·q08 근거 답변, q09·q10 보류. 일부·상충 근거와 문서 지시문 처리 검증 |
| Streamlit 화면 | 예시·대화 기록·출처 펼치기·안전한 오류·세션 10회 제한. 실제 브라우저 3문항 검증 |
| Phase 5 평가 | 기존 평가와 비교 답변·AI 채점 각 120개, 재현 가능한 지표, 대기 중인 사람 검토 목록 34건 |
| 배포 준비 | 사전 계산 벡터 번들과 서버 설정. [배포 안내](DEPLOYMENT.md), 공개 URL은 대기 |
| 개발 단계 | 영문·국문 Phase 문서 5개와 최신 현황 점검·우선순위별 로드맵 |

`app.py`가 검증한 `rag.py`를 호출하고 `grounding.py`가 주장·인용을 검증합니다. `eval/evaluate.py`는 기존 10문항 결과를 보존하고 `eval/benchmark.py`는 설정 비교와 확대 실행 검증을 담당합니다. `tracing.py`는 선택적인 LangSmith 실패를 답변과 분리합니다. 현재 증빙은 [Phase 4](Phase/Phase4_StreamlitInterface.md)와 [Phase 5 보고서](Phase/Phase5_EvaluationAndDeployment.md)에 있습니다. 소스 저장소는 [SoyeonAhn3/enterprise-rag](https://github.com/SoyeonAhn3/enterprise-rag)이며 **검증한 공개 데모 URL은 아직 없습니다.**

## 로컬 실행

Python 3.12와 Git을 설치한 뒤 PowerShell에서 프로젝트를 내려받고 실행 의존성을 설치합니다.

```powershell
git clone https://github.com/SoyeonAhn3/enterprise-rag.git
Set-Location enterprise-rag
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path -LiteralPath .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
```

로컬 `.env`에 `ANTHROPIC_API_KEY`를 설정한 뒤 저장소 루트에서 실행합니다. 기존 `.env`와 설정은 유지합니다. 앱은 번들의 사전 계산 벡터를 자동으로 가져오고 최초 실행 때 공개 질문 임베딩 모델을 다운로드하므로, 고정 문서의 인덱스를 직접 만드는 과정은 선택 사항입니다.

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

Streamlit이 출력하는 로컬 주소를 열고 예시 질문을 선택합니다. 답변 생성에는 운영자의 Claude 키를 사용하며 API 사용량이 발생합니다. 방문자는 인증 정보를 입력하지 않습니다. 서버 설정과 공개 배포 검사는 [DEPLOYMENT.md](DEPLOYMENT.md)를 따릅니다.

### 오프라인 검사 및 개발

아래 검사는 로컬 문서·저장된 평가 결과·테스트 대역을 사용하며 API 인증 정보나 새 모델 호출이 필요하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -X utf8 ingest.py --dry-run
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
.\.venv\Scripts\python.exe -X utf8 -m eval.benchmark verify --output-dir eval/results/phase5_v2_20261014
```

Dry run은 API 인증 정보나 임베딩 호출 없이 `data/chunks_preview.json`을 생성합니다. 현재 문서 기준 결과는 **문서 4개, 텍스트 페이지 13개, 제외 페이지 0개, 청크 22개**입니다. 미리보기는 로컬 생성 파일이며 Git에서 제외합니다.

### 인덱싱 및 명령줄 답변

인덱싱과 검색에는 API 키가 필요 없습니다. 최초 실행 시 공개 모델 `intfloat/multilingual-e5-small`을 `data/embedding_models/`에 다운로드하며 로컬 크기는 약 487 MB입니다. 이후 CPU에서 재사용합니다. `.env`와 모델 캐시는 Git에서 제외합니다.

```powershell
# API 키 불필요. 최초 생성 시 로컬 모델 다운로드
.\.venv\Scripts\python.exe -X utf8 ingest.py
.\.venv\Scripts\python.exe -X utf8 rag.py "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
.\.venv\Scripts\python.exe -X utf8 -m eval.check_retrieval
```

PDF·임베딩 모델·차원·청크 설정이 바뀌거나 기존 OpenAI 인덱스에서 전환할 때는 `ingest.py --rebuild`를 사용합니다. 일치하는 인덱스는 모델 로딩이나 문서 재임베딩 없이 재사용합니다. 기본 로컬 모델은 384차원이며 문서에는 `passage: `, 질문에는 `query: ` 접두어를 적용합니다. 설정 우선순위는 환경변수 → 전달된 서버 시크릿 → `.env` → 기본값입니다. 최초 다운로드 후에는 `EMBEDDING_LOCAL_FILES_ONLY=true`로 오프라인 로딩할 수 있습니다. 새 환경에서는 캐시를 만들 때까지 `false`로 둡니다.

검색 검증 도구는 q01·q07·q08의 검색 청크 전체와 페이지·근거 발췌 일치를 `data/retrieval_smoke.json`에 저장합니다. 실제 로컬 모델로 세 문항 모두 통과했으며, 문서 임베딩을 금지한 새 프로세스에서도 오프라인으로 검색했습니다. 고정 문서의 오프라인 작업 흐름이므로 재생성 전에 앱을 멈추고 이후 검색기를 다시 시작합니다. 이전 비활성 컬렉션은 저장소에 남지만 검색하지 않습니다.

Claude를 사용하려면 로컬 `ANTHROPIC_API_KEY`를 설정하고 `.\.venv\Scripts\python.exe -X utf8 llm.py --check`를 실행합니다. 답변 생성 없이 모델 접근 가능 여부를 검사합니다. 기본 `ANTHROPIC_MODEL`은 `claude-sonnet-5-5`이며 요청 제한 시간 30초, 자동 재시도 0회, 기본 출력 한도 2048토큰을 적용합니다. OpenAI 키를 Claude 키로 사용할 수 없습니다. [Anthropic은 자체 임베딩을 제공하지 않으므로](https://platform.claude.com/docs/en/build-with-claude/embeddings) 로컬 검색은 Claude 인증 정보와 별개로 동작합니다.

```powershell
# 근거 기반 답변 1회. 설정한 Claude 키를 사용하며 API 사용량이 발생합니다.
.\.venv\Scripts\python.exe -X utf8 rag.py --answer "부가세 제외 구매 금액이 정확히 100만원이라면 최종 결재권자는 누구인가요?"
# 실제 질문 5개. 전체 결과를 data/answer_smoke.json에 기록합니다.
.\.venv\Scripts\python.exe -X utf8 -m eval.check_answers
```

`--answer`가 없으면 기존 검색 전용 동작을 유지합니다. Python에서는 `RAGAssistant(retriever, client).answer(question)`을 사용하고 사용 후 호출자가 `Retriever`·`ClaudeClient`를 종료합니다. 전체 예제는 [Phase 3 보고서](Phase/Phase3_GroundedAnswers.md)에 있습니다. 반환값은 `answer`, `answerable`, 주장별 인용문, 검증한 `sources`, 전체 `retrieved_chunks`, 검색·생성·전체 처리 시간을 포함합니다. 초기화 시간은 제외합니다.

근거 부족 시 정확히 `등록된 문서에서 해당 정보를 확인할 수 없습니다.`를 반환하고 출처를 인용하지 않습니다. API 실패와 잘못된 출력은 정상 보류와 구분된 예외입니다. 인용문은 공백 차이만 허용하여 검색 원문과 대조하고 파일명·페이지는 저장된 메타데이터를 사용합니다. 인용문 일치는 출처를 확인하는 검사이며 의미적 정확성에는 별도 검토가 필요합니다.

## 프로젝트 자료 살펴보기

로컬 채팅 화면은 다음 명령으로 실행합니다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

서버가 `.env` 또는 Streamlit Secrets를 읽고 방문자에게 키를 입력받지 않습니다. 신규 환경에서는 문서를 임베딩하지 않고 `deployment/index_bundle.json`을 가져온 뒤 공개 질문 모델을 최초 1회 다운로드합니다. 캐시한 리소스가 모델·인덱스·클라이언트를 재사용합니다. 세션당 기본 10회이며 실패 요청도 차감합니다. 공개 공유에는 제공업체 전체 예산 제어도 필요합니다.

![로컬 Streamlit 초기 화면](docs/evidence/local-home.png)

[대화 스크린샷](docs/evidence/local-chat.png)은 실제 로컬 답변·출처 발췌·보류를 보여 줍니다. Cloud 설정, 시크릿, 재시작 검사, 선택적 추적 검증은 [DEPLOYMENT.md](DEPLOYMENT.md)에 있습니다.

출처 발췌에서 PDF 줄바꿈으로 끊긴 한글 단어는 고정 문서에 붙여 쓴 형태가 확인될 때 연결하고, 화면에서는 단어 단위로 줄을 바꿉니다. 원문 증빙은 보존합니다. [줄바꿈 수정 보고서](Phase/Phase4_StreamlitInterface.md#출처-발췌-줄바꿈-수정--2026-10-14)에 데스크톱·모바일 화면과 회귀 검사 결과를 기록했습니다.

1. [MVP 기획서](plan/enterprise_rag_assistant_streamlit_mvp_plan.md)에서 구현 요구사항과 배포 계획을 확인합니다.
2. [샘플 문서 안내](rag_mvp_sample_documents/README.md)에서 문서 구성과 평가 근거 판정 방식을 확인합니다.
3. [실행용 평가 데이터셋](eval/questions.json)에서 질문, 참고 정답, 채점 기준을 살펴봅니다. 검토한 원본은 샘플 문서 폴더에 보존되어 있습니다.

기획서, 샘플 문서 안내, PDF, 평가 데이터의 내용은 한국어로 작성되어 있습니다.

## 샘플 문서

가상 기업 **가온비즈(Gaonbiz)**의 구매·결재·IT 보안·계약·정산 업무를 다룹니다. 문서 4개 모두 버전은 `1.0`, 시행일은 `2026-09-01`로 통일되어 있습니다.

| 문서 | ID | 페이지 수 | 주요 내용 |
| --- | --- | ---: | --- |
| [구매요청 및 발주 업무지침](rag_mvp_sample_documents/01_purchase_process.pdf) | GB-PUR-01 | 3 | 구매요청, 비교견적, 발주, 긴급 구매 |
| [결재권한 및 예산통제 규정](rag_mvp_sample_documents/02_approval_budget.pdf) | GB-APR-02 | 3 | 금액별 결재권자, 예산 검토, 동일 목적 구매 합산 |
| [IT 자산 및 SaaS 보안검토 지침](rag_mvp_sample_documents/03_it_security.pdf) | GB-SEC-03 | 3 | 사전 보안검토, 무료 체험, 검토 기간, 자산 등록 |
| [계약 검토·검수·정산 업무가이드](rag_mvp_sample_documents/04_contract_settlement.pdf) | GB-CON-04 | 4 | 법무 검토, 납품 검수, 지급 증빙, 정산 일정 |

모든 문서는 데모용 합성 자료입니다. 규정과 금액 기준은 실제 기업의 정책을 나타내지 않으며, 실제 구매·계약 업무에 사용해서는 안 됩니다.

## MVP 구조

구현한 파이프라인은 **검색 1회 후 답변을 생성하는 2-Step RAG**를 사용합니다.

1. PDF를 페이지별로 추출하고 텍스트를 분할하며 `source_file`, `page`, `chunk_id` 메타데이터를 보존합니다.
2. 문서 임베딩을 생성하고 배포 전에 고정 Chroma 인덱스를 구축합니다.
3. 사용자 질문을 임베딩하고 관련 청크 상위 3개를 검색합니다.
4. 검색된 근거로 한국어 답변을 생성하고, 근거가 부족하면 답변을 보류합니다.
5. 검증된 출처의 파일명, 1부터 시작하는 페이지 번호, 발췌를 표시합니다.
6. 검색·생성 과정을 추적하고 준비된 질문으로 애플리케이션을 평가합니다.

초기 청크 설정은 **약 800자**, **중복 120자**입니다. 기획서의 시작 설정이며, 측정으로 확인한 최적값은 아닙니다.

| 영역 | 기술 / 상태 |
| --- | --- |
| 애플리케이션·UI | Python, Streamlit |
| PDF 추출 | PyMuPDF |
| RAG 처리·청크 분할 | LangChain, langchain-text-splitters |
| 벡터 인덱스 | Chroma, langchain-chroma |
| 임베딩 | FastEmbed / ONNX Runtime, 로컬 다국어 E5 |
| 답변 생성 | Anthropic Claude API, 공식 Python SDK |
| 실행 추적 | LangSmith 연동 구현, 실제 원격 Trace 대기 |
| 평가 | Python, JSON, AI 채점. 사람 검토 대기 |
| 배포 | Streamlit Community Cloud 예정, 공개 검증 대기 |

Windows / Python 3.12.10과 고정 의존성으로 로컬 검증했습니다. 기존 패키지 교체 없이 Streamlit 1.65.0을 추가했고 `pip check`를 통과했습니다. LangSmith HTTP 계약과 추적 비활성·실패 처리는 테스트했지만 실제 Trace에는 운영자 키가 필요합니다. Cloud 호환성·메모리·모델 캐시 시작·공개 재시작 동작은 아직 미검증이며 로컬 Linux Docker 데몬도 실행되지 않았습니다.

## 평가 설계

기존 평가셋은 **단일 문서 질문 6개, 다중 문서 질문 2개, 답변 불가능한 질문 2개**로 구성됩니다. 금액 경계, 기한, 결재·검토 요건, 답변 보류를 확인합니다. 별도 [v2 데이터셋](eval/questions_v2.json)은 [Phase 5 기준](Phase/Phase5_EvaluationAndDeployment.md)에 따라 개발용 40개·최종 확인용 20개로 확장했습니다.

답변 가능한 질문에는 필요한 사실별로 `evidence_groups`를 정의합니다. 그룹 사이는 **AND**, 그룹 안의 `any_of` 후보 사이는 **OR**로 판정합니다. 각 후보에는 `document`, `page`, 원문 발췌인 `quote`가 들어 있습니다. 대체 근거가 하나 충족되면 인정하며, 모든 대체 페이지를 요구하지 않습니다.

예를 들어 q07은 결재권자 근거와 보안검토 근거가 모두 필요합니다. 보안검토 요건은 `03_it_security.pdf`의 1쪽 또는 3쪽으로 확인할 수 있습니다.

| 기존 평가 항목 | 정의 |
| --- | --- |
| Retrieval Hit@3 | 답이 있는 8문항 중 검색된 상위 3개 청크에 허용된 문서·페이지가 하나 이상 포함된 질문의 비율 |
| Multi-document Coverage | 다중 문서 질문 2개 각각에서 모든 필수 근거 그룹의 후보 페이지가 하나 이상 상위 3개에 포함됐는지 확인 |
| Answer Correctness | 10개 답변을 참고 정답과 `grading_criteria`에 따라 사람이 검토하며, 핵심 주장이 검색된 근거로 뒷받침되는지도 확인 |
| Abstention | 문서에 답이 없는 질문 2개에서 적절하게 답변을 보류하는지 확인 |
| Latency | 질문 10개에 대한 평균 응답 시간 |

페이지가 일치하더라도 필요한 문장이 검색됐다고 단정할 수 없습니다. 실제 청크에 근거가 포함됐는지도 검토해야 합니다. `answer_keywords`는 검토 보조 정보이며 자동 정답 판정 기준이 아닙니다.

**평가 데이터셋을 인덱싱하거나 참고 정답·근거 주석·채점 기준을 생성에 전달하지 않습니다.** 검사할 현재 질문만 RAG에 전달하며 근거는 검색된 PDF 본문에서 가져옵니다. 답변 불가능한 질문의 `evidence_groups`는 빈 목록입니다. 해당 질문은 검색 적중률과 다중 문서 Coverage에서 제외하며, 빈 목록을 근거 확보 성공으로 처리하지 않습니다.

Phase 2에서 실제 로컬 E5로 q01·q07·q08을 검사했고, Phase 5에서는 아래와 같이 전체 10문항을 기록했습니다. 소규모 합성 평가셋은 실제 기업 문서의 성능을 입증하지는 않습니다.

[2026-10-14 실행 원본](eval/results/phase5_baseline.json)은 `claude-sonnet-5-5`와 기존 청크 22개 인덱스를 사용했고 10회 모두 오류 없이 완료했습니다. [에이전트 검토](eval/results/phase5_agent_review.json)와 대기 중인 [사람 검토](eval/results/phase5_human_review.template.json)를 명확히 구분합니다.

| 실측 항목 | 값 |
| --- | --- |
| Retrieval Hit@3 / 다중 문서 Coverage | 8/8 / 2/2 |
| 필수 원문 발췌 전체 검색 | 8/8 |
| 답변 불가 질문 보류 | 2/2 |
| 평균 RAG 처리 시간 | 3326.96 ms, 초기화 제외 |
| 에이전트 검토 정답 / 근거 충족 | 9/10 / 10/10 |

q08은 근거 있는 CFO·법무 검토 결론을 제시했지만 일반 적용 기준과 명확한 시점 설명이 전체 채점 기준에 부족했습니다. 해당 일반 조항은 검색되지 않았습니다. 검색 성공을 정답으로 간주하지 않고 전체 기준상 오답으로 기록했으며 참고 정답을 모델에 전달하지 않았습니다. [Phase 5 분석](Phase/Phase5_EvaluationAndDeployment.md)에 상세 근거가 있습니다.

```powershell
# 과금되는 신규 요청 10회. 실행마다 새 시간명 파일에 중간 결과까지 저장
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate
# API 호출 없는 지표 재계산
.\.venv\Scripts\python.exe -X utf8 -m eval.evaluate --report eval/results/phase5_baseline.json --review eval/results/phase5_agent_review.json
```

추적은 로컬 `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`를 설정한 뒤 프로젝트 가상환경으로 `python -m eval.check_trace`를 실행합니다. 설정 누락·추적 실패는 답변을 막지 않으며 검증기는 실제 원격 검색·생성 실행을 요구합니다. 현재 키와 실제 Trace 증빙은 없습니다.

## 개발 순서와 범위

[MVP 기획서](plan/enterprise_rag_assistant_streamlit_mvp_plan.md)의 범위를 따릅니다. Phase 4는 로컬 완료이며 실제 추적·공개 배포를 검증하기 전까지 Phase 5는 진행 중으로 유지합니다. 전체 사람 채점은 Phase 5에 기록된 결정에 따라 뒤로 미뤘으며 미검증으로 명시합니다. [최신 로드맵](Phase/DevelopmentStatusAndRoadmap.md)에 남은 배포 작업과 이후 단계 제안을 정리했습니다.

| Phase | 목표 | 상태 |
| --- | --- | --- |
| [1 — 개발 기반](Phase/Phase1_Foundation.md) | 환경·고정 문서·페이지 메타데이터·청크 분할 검증 | ✅ 완료; 테스트 35개 통과 |
| [2 — 인덱싱·검색](Phase/Phase2_IndexingAndRetrieval.md) | Chroma 인덱스 생성·재로딩 및 상위 3개 청크 검색 | ✅ 실제 로컬 임베딩 검증 완료 |
| [3 — 근거 기반 답변](Phase/Phase3_GroundedAnswers.md) | 근거 있는 답변 생성·출처 검증·답변 보류 | ✅ 실제 Claude 검증 완료 |
| [4 — Streamlit 화면](Phase/Phase4_StreamlitInterface.md) | 채팅·출처 표시·로딩과 오류·사용량 제한 | ✅ 로컬 브라우저 검증 완료 |
| [5 — 평가·배포](Phase/Phase5_EvaluationAndDeployment.md) | 기존 10문항 보존·60문항 비교·실행 추적 검증·공개 데모 배포 | 🚧 확대 AI 평가·오프라인 검증 완료, 사람 검토·원격 검사 대기 |

기존 2일 목표에 대응하면 Day 1은 Phase 1~4의 로컬 동작, Day 2는 Phase 5의 평가·배포입니다. 시간 경과가 아니라 검증 근거를 기준으로 완료를 판단합니다. 각 Phase 문서는 상단 영문, 하단 국문으로 구성했습니다.

MVP는 고정된 문서를 사용합니다. 사용자 파일 업로드, OCR, 복잡한 표 인식, 인증·문서 권한, 에이전트 기반 검색이나 재검색, Hybrid Search, Reranker, 장기 Memory는 이번 범위에서 제외합니다.

## 현재 프로젝트 구조

```text
Enterprise-rag/
├── Phase/
│   ├── DevelopmentStatusAndRoadmap.md       # 현재 상태 점검과 다음 개발 우선순위
│   ├── Phase1_Foundation.md                 # ✅ 완료
│   ├── Phase2_IndexingAndRetrieval.md       # ✅ 로컬 모델 인수 검증 완료
│   ├── Phase3_GroundedAnswers.md            # ✅ 근거 답변 검증 완료
│   ├── Phase4_StreamlitInterface.md         # ✅ 로컬 브라우저 검증 완료
│   └── Phase5_EvaluationAndDeployment.md    # 🚧 원격 완료 조건 대기
├── .streamlit/                             # 테마 및 서버 시크릿 템플릿
├── deployment/index_bundle.json            # 검토한 사전 계산 벡터
├── docs/evidence/                          # 실제 로컬 브라우저 스크린샷
├── documents/                              # 실행용 PDF 4개
├── eval/
│   ├── __init__.py
│   ├── check_retrieval.py                  # q01·q07·q08 검색 검증
│   ├── check_answers.py                    # 실제 근거 답변 5문항 검사
│   ├── evaluate.py                         # 10문항 실행 및 오프라인 지표
│   ├── benchmark.py                        # 비교 평가·집계·읽기 전용 검증
│   ├── ai_review.py                        # 참고 근거 기반 AI 채점·사전 시험
│   ├── expanded_cases.py                   # 버전별 데이터셋·PDF 근거 검사
│   ├── render_report.py                    # 검증된 Markdown·CSV 내보내기
│   ├── check_trace.py                      # 실제 LangSmith 하위 실행 재조회
│   ├── results/                            # 실행·지표·에이전트/사람 검토 파일
│   ├── questions.json                      # 기존 평가 질문 10개
│   └── questions_v2.json                   # 개발용 40개·최종 확인용 20개
├── plan/
│   └── enterprise_rag_assistant_streamlit_mvp_plan.md
├── rag_mvp_sample_documents/                # 검토한 원본 자료
├── tests/
│   ├── __init__.py
│   ├── fakes.py                            # 분리된 테스트 임베딩
│   ├── test_ingest.py
│   ├── test_config_and_embeddings.py
│   ├── test_claude.py
│   ├── test_index_and_retrieval.py
│   ├── test_retrieval_checks.py
│   ├── test_grounding.py
│   ├── test_answers.py
│   ├── test_answer_checks.py
│   ├── test_evaluation.py
│   ├── test_benchmark.py
│   ├── test_benchmark_artifacts.py
│   ├── test_tracing.py
│   ├── test_deployment.py
│   ├── test_app.py
│   └── test_source_display.py
├── app.py                                  # 한국어 Streamlit 채팅 화면
├── app_runtime.py                          # RAG 리소스 재사용 및 수명 관리
├── source_display.py                       # 원문 증빙을 보존하는 발췌 표시
├── config.py
├── embeddings.py
├── deployment.py                           # 인덱스 번들 내보내기·가져오기·검증
├── tracing.py                              # 선택적 LangSmith 실행 추적
├── grounding.py                            # 프롬프트·엄격한 JSON·인용 검증
├── llm.py                                  # Claude 호출 및 연결 검사
├── index_store.py
├── ingest.py                               # 미리보기·인덱스 생성·재사용·재생성
├── rag.py                                  # 검색 및 근거 답변 (--answer)
├── .env.example
├── .gitignore
├── .python-version
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── DEPLOYMENT.md                           # 영문·국문 배포 안내
└── README_ko.md
```

`documents/`와 `eval/questions.json`은 검토한 샘플 자료의 실행용 복사본입니다. 데이터 변경 시 양쪽을 맞춰야 합니다. 인증 정보, 생성 미리보기·검색 결과, 다운로드 모델, 로컬 Chroma DB, 가상환경은 Git에서 제외합니다.
