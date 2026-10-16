# Phase 6: 기존 60문항 품질 회귀 평가

이미 확인한 60문항으로 개선 효과를 점검했다. 새로운 문제에 대한 일반 정확도는 아니다.
답변과 별도 AI 채점은 같은 모델을 사용했다. 사람의 판정은 아직 완료하지 않았다.
두 설정은 동일한 PDF·인덱스·모델·답변 프롬프트를 사용한다. pages는 후보 검색 수와 문맥 구성 방식을 함께 바꾼다.

| 지표 | chunks/5 | pages/5 |
|---|---:|---:|
| AI 기준 통과 | 14/60 | 14/60 |
| 답변 가능 질문 AI 통과 | 12/48 | 12/48 |
| 필수 근거 인용문 전부 포함 | 37/48 | 47/48 |
| 근거 그룹 회수 | 62/75 | 74/75 |
| 모르는 질문 답변 보류 | 12/12 | 12/12 |
| 세부 채점 기준 충족 | 28/107 | 28/107 |
| 평균 문맥 글자 수 | 3153.4 | 4222.5 |
| 평균 답변 시간(초) | 4.02 | 4.09 |
| 생성 입력 토큰(캐시 제외) | 294912 | 359721 |
| 생성 출력 토큰 | 24563 | 24049 |

두 방식 모두 AI 채점 가능한 문항: 14/60.
pages에서 통과로 바뀐 문항: q08.
pages에서 실패로 바뀐 문항: 없음.
직접 비교할 수 없는 문항: q15, q16, q17, q18, q19, q20, q21, q22, q23, q24, q25, q26, q27, q28, q29, q30, q31, q32, q33, q34, q35, q36, q37, q38, q39, q40, q41, q42, q43, q44, q45, q46, q47, q48, q49, q50, q51, q52, q53, q54, q55, q56, q57, q58, q59, q60.

## 사람의 확인이 필요한 항목

reference_quote_missing은 정답표의 인용문이 문맥에 전부 없다는 뜻이다. 의미상 답변이 불가능하다는 판정은 아니다.
ai_incorrect_with_complete_evidence는 근거가 있는데도 AI 기준을 통과하지 못한 경우다. 실제 답변 누락과 채점 문제를 함께 살펴야 한다.

### chunks5

- q08: ai_incorrect_with_complete_evidence, ai_unsupported_answer
- q16: judge_error_or_missing
- q17: judge_error_or_missing
- q18: judge_error_or_missing
- q19: judge_error_or_missing
- q20: judge_error_or_missing
- q21: judge_error_or_missing
- q22: judge_error_or_missing
- q23: judge_error_or_missing
- q24: judge_error_or_missing
- q25: reference_quote_missing, judge_error_or_missing
- q26: judge_error_or_missing
- q27: judge_error_or_missing
- q28: reference_quote_missing, judge_error_or_missing
- q29: reference_quote_missing, judge_error_or_missing
- q30: reference_quote_missing, judge_error_or_missing
- q31: reference_quote_missing, judge_error_or_missing, answerable_abstention
- q32: reference_quote_missing, judge_error_or_missing
- q33: judge_error_or_missing
- q34: judge_error_or_missing
- q35: judge_error_or_missing
- q36: judge_error_or_missing
- q37: judge_error_or_missing
- q38: judge_error_or_missing
- q39: judge_error_or_missing
- q40: judge_error_or_missing
- q41: judge_error_or_missing
- q42: judge_error_or_missing
- q43: judge_error_or_missing
- q44: judge_error_or_missing
- q45: judge_error_or_missing
- q46: judge_error_or_missing
- q47: judge_error_or_missing
- q48: judge_error_or_missing
- q49: judge_error_or_missing
- q50: judge_error_or_missing
- q51: reference_quote_missing, judge_error_or_missing, answerable_abstention
- q52: judge_error_or_missing
- q53: reference_quote_missing, judge_error_or_missing, answerable_abstention
- q54: reference_quote_missing, judge_error_or_missing
- q55: reference_quote_missing, judge_error_or_missing, answerable_abstention
- q56: reference_quote_missing, rag_error_or_missing
- q57: judge_error_or_missing
- q58: judge_error_or_missing
- q59: judge_error_or_missing
- q60: judge_error_or_missing

### pages5

- q15: judge_error_or_missing
- q16: judge_error_or_missing
- q17: judge_error_or_missing
- q18: judge_error_or_missing
- q19: judge_error_or_missing
- q20: judge_error_or_missing
- q21: judge_error_or_missing
- q22: judge_error_or_missing
- q23: judge_error_or_missing
- q24: judge_error_or_missing
- q25: rag_error_or_missing
- q26: judge_error_or_missing
- q27: judge_error_or_missing
- q28: judge_error_or_missing
- q29: judge_error_or_missing
- q30: rag_error_or_missing
- q31: judge_error_or_missing
- q32: judge_error_or_missing
- q33: judge_error_or_missing
- q34: judge_error_or_missing
- q35: judge_error_or_missing
- q36: judge_error_or_missing
- q37: judge_error_or_missing
- q38: judge_error_or_missing
- q39: judge_error_or_missing
- q40: judge_error_or_missing
- q41: judge_error_or_missing
- q42: judge_error_or_missing
- q43: judge_error_or_missing
- q44: judge_error_or_missing
- q45: judge_error_or_missing
- q46: judge_error_or_missing
- q47: judge_error_or_missing
- q48: judge_error_or_missing
- q49: judge_error_or_missing
- q50: judge_error_or_missing
- q51: reference_quote_missing, judge_error_or_missing, answerable_abstention
- q52: judge_error_or_missing
- q53: judge_error_or_missing
- q54: judge_error_or_missing
- q55: judge_error_or_missing
- q56: rag_error_or_missing
- q57: judge_error_or_missing
- q58: judge_error_or_missing
- q59: judge_error_or_missing
- q60: judge_error_or_missing

## 재현과 한계

- protocol.json: 실행 전에 고정한 조건, 원문·코드·질문·프롬프트의 해시.
- attempts/: 요청 전 pending 기록, 완료 후 원문 답변/AI 채점 기록. 중단된 요청은 자동 재시도하지 않는다.
- answers.json: 120개 답변 시도와 120개 채점 기록. 오류도 분모에 남긴다.
- summary.json: 수치, 개선/회귀 문항, AI가 지적한 문장과 근거. 채점 오류를 사람이 수정한 결과는 아니다.
- 설정별 각 질문에 한 번씩 답했다. 모델·AI 채점의 실행 간 변동이나 통계적 유의성을 측정하지 않았다.
- verify/report는 API 호출 없이 저장된 인용·채점 원문·기록 연결을 다시 검증한다.
- 지연시간은 이 로컬 순차 답변 실행의 관찰값이다. 동시 접속/Cloud 성능 시험은 진행하지 않았다.
- LangSmith 원격 추적 검증은 별도 단건 점검이다. 이 배치 평가에서는 tracing을 끈다.
