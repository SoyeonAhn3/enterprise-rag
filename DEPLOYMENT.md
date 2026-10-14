# Deployment / 배포 안내

## English

Target repository: [SoyeonAhn3/enterprise-rag](https://github.com/SoyeonAhn3/enterprise-rag). The owner confirmed that the GitHub account is connected to Streamlit. **No public demo URL has been deployed or verified yet.** The repository initially contained only its title README; publishing uses a separate clean checkout so the parent workspace's unrelated Git remote is preserved.

The local environment is Python **3.12.10** with the pinned `requirements.txt`. Local browser checks passed for two answerable questions and one unanswerable question. Evidence: [home screen](docs/evidence/local-home.png), [answers and source excerpts](docs/evidence/local-chat.png). These are local screenshots, not proof of a public deployment.

### Precomputed index

`deployment/index_bundle.json` contains 22 original chunks, metadata, and precomputed 384-dimensional vectors from the public synthetic PDFs. Its 208,225 bytes are portable JSON; `.env`, native Chroma storage, and the 487 MB model cache are excluded. On a fresh server, `deployment.ensure_index()` imports those vectors into Chroma. On subsequent starts it validates and reuses the native index. It does not extract or embed PDFs during startup.

PDF hashes, embedding/chunk settings, extraction-library versions, vector dimensions, record hashes, and the bundle checksum must match. A conflicting or damaged index produces an error rather than being silently rebuilt. If documents/settings change, rebuild offline and export a new bundle to a new path, review it, then replace the published artifact deliberately.

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
# Optional: materialize the bundled vectors before launching the app.
.\.venv\Scripts\python.exe -X utf8 deployment.py import
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

The bundle's first import and reload were tested with the real local query model while document embedding was prohibited. Linux/Community Cloud execution remains unverified: Docker was installed locally but its Linux daemon was unavailable.

### Community Cloud setup

1. Publish the reviewed files to `SoyeonAhn3/enterprise-rag`, branch `main`.
2. In Streamlit Community Cloud, create an app from that repository, branch `main`, entrypoint `app.py`. Select Python **3.12** in Advanced settings; do not rely on an unspecified default.
3. Copy the **setting names** from [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example) into the server's Secrets settings and supply the operator's Claude key there. Keep `EMBEDDING_LOCAL_FILES_ONLY=false` on a new server so the public query model can download. Never commit real secrets.
4. The operator must set appropriate provider-side usage limits/budget alerts before sharing. `SESSION_QUESTION_LIMIT=10` limits attempts per browser session, including failed requests; it can be bypassed with a new session and is not an account-wide spending cap.
5. Start the app, inspect startup logs and memory, then test q01, q07, and q09 in a fresh/private browser context. Confirm answers, filenames, 1-based pages, excerpts, and abstention without any visitor key entry.
6. Reboot the app and repeat a query. Verify index loading/import and model-cache behavior. Record the actual URL and observed results in both READMEs and Phase 5 only after these checks pass.

The first model download and ONNX memory use can affect Cloud startup. A successful local run or bundle import does not establish Cloud capacity. Official references: [deployment settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [server secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [dependencies](https://docs.streamlit.io/deploy/concepts/dependencies).

### Optional LangSmith verification

Set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, and the appropriate regional `LANGSMITH_ENDPOINT` in the server environment or local `.env`. Tracing sends question/context/output payloads, so this demo uses synthetic public documents. Keys and settings objects are never included in trace payloads. Missing configuration or a failed write disables the sink while answers continue; restart the process after correcting a failed trace configuration.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace
```

This makes one Claude call, then reads the root and retrieval/generation child runs back from LangSmith. The private run URL is saved locally in ignored `data/trace_check.json`. It does not publish a trace or enable a public share link. Without a configured key, the command stops before making a billable generation. See [LangSmith custom instrumentation](https://docs.langchain.com/langsmith/annotate-code).

## 한국어

배포 대상은 [SoyeonAhn3/enterprise-rag](https://github.com/SoyeonAhn3/enterprise-rag)이며 사용자가 Streamlit과 GitHub 계정 연결을 확인했다. **실제 공개 URL 배포·검증은 아직 하지 않았다.** 원격 저장소에는 제목 README만 있었으며, 상위 작업 폴더의 다른 Git 원격을 유지하기 위해 분리된 체크아웃에서 게시를 준비한다.

로컬은 Python **3.12.10**과 버전 고정한 `requirements.txt`로 검증했다. 실제 브라우저에서 답변 가능 2문항·불가능 1문항을 확인했다. 증빙: [초기 화면](docs/evidence/local-home.png), [답변 및 출처 발췌](docs/evidence/local-chat.png). 공개 배포 화면이 아닌 로컬 화면이다.

### 사전 생성 인덱스

`deployment/index_bundle.json`은 공개 합성 PDF의 원문 청크 22개, 메타데이터, 사전 계산한 384차원 벡터를 담은 208,225바이트 JSON이다. `.env`, Chroma 네이티브 저장소, 약 487 MB 모델 캐시는 포함하지 않는다. 신규 서버에서는 `deployment.ensure_index()`가 벡터를 Chroma에 가져오고 다음 시작부터 검증 후 재사용한다. 시작 시 PDF 추출·문서 임베딩을 수행하지 않는다.

PDF 해시, 임베딩·청크 설정, 추출 라이브러리 버전, 벡터 차원, 레코드 해시, 번들 체크섬을 검증한다. 충돌·손상한 인덱스는 자동 재생성하지 않고 오류로 처리한다. 문서·설정이 바뀌면 오프라인에서 재생성하고 새 경로로 내보낸 번들을 검토한 뒤 게시 파일을 교체한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 deployment.py check
# 앱 실행 전에 사전 계산 벡터를 가져올 때 사용
.\.venv\Scripts\python.exe -X utf8 deployment.py import
.\.venv\Scripts\python.exe -X utf8 -m streamlit run app.py
```

첫 가져오기와 재로딩은 문서 임베딩을 금지하고 실제 로컬 질문 모델로 검증했다. Linux·Community Cloud 실행은 미검증이다. 로컬 Docker는 설치되어 있지만 Linux 데몬이 실행되지 않아 해당 환경 검사를 하지 못했다.

### Community Cloud 설정

1. 검토한 파일을 `SoyeonAhn3/enterprise-rag`의 `main`에 게시한다.
2. Streamlit Community Cloud에서 해당 저장소·`main`·진입 파일 `app.py`로 앱을 생성한다. Advanced settings에서 Python **3.12**를 직접 선택한다.
3. [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example)의 **설정 이름**을 서버 Secrets에 옮기고 운영자의 Claude 키를 서버에 입력한다. 신규 서버의 `EMBEDDING_LOCAL_FILES_ONLY`는 `false`로 두어 공개 질문 모델을 다운로드한다. 실제 키는 커밋하지 않는다.
4. 공개 공유 전 운영자가 제공업체 사용량 제한·예산 알림을 설정한다. `SESSION_QUESTION_LIMIT=10`은 실패를 포함한 브라우저 세션별 요청 제한이며 새 세션으로 우회할 수 있다. 계정 전체 비용 제한을 대신하지 않는다.
5. 시작 로그와 메모리를 확인한 뒤 새 창·시크릿 창에서 q01·q07·q09를 실행한다. 방문자 키 입력 없이 답변·파일명·1-based 페이지·발췌·보류가 동작하는지 확인한다.
6. 앱을 재시작하고 다시 질문하여 인덱스 로딩·가져오기와 모델 캐시 동작을 확인한다. 통과한 후 실제 URL과 결과를 양쪽 README·Phase 5에 기록한다.

최초 모델 다운로드와 ONNX 메모리 사용이 Cloud 시작에 영향을 줄 수 있다. 로컬 실행·번들 가져오기를 Cloud 자원 검증으로 간주하지 않는다. 공식 자료: [배포 설정](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [서버 시크릿](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management), [의존성](https://docs.streamlit.io/deploy/concepts/dependencies).

### 선택적 LangSmith 검증

서버 환경 또는 로컬 `.env`에 `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT`, 해당 지역의 `LANGSMITH_ENDPOINT`를 설정한다. 질문·문맥·출력을 전송하므로 공개 합성 문서를 사용한다. 키와 설정 객체를 추적 내용에 포함하지 않는다. 설정 누락 또는 전송 실패 시 추적을 중단해도 답변은 계속 동작한다. 실패한 추적 설정을 수정한 뒤에는 프로세스를 재시작한다.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m eval.check_trace
```

Claude 1회 호출 후 LangSmith에서 루트와 검색·생성 하위 실행을 다시 읽어 검증한다. 비공개 실행 URL은 Git에서 제외한 `data/trace_check.json`에 저장한다. 추적을 공개하거나 공개 공유 링크를 만들지 않는다. 키가 없으면 과금되는 생성 전에 중단한다. [LangSmith 공식 계측 안내](https://docs.langchain.com/langsmith/annotate-code)를 참고한다.
