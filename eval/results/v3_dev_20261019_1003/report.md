# 데이터셋 품질 평가 — dev / 20문항

같은 합성 PDF의 지정 문항을 평가했다. 외부 독립 평가나 사람 검증을 완료했다는 뜻은 아니다.
답변과 별도 AI 채점은 같은 모델을 사용한다. 최종 평가 결과를 개선에 사용하면 이후에는 회귀 사례로 취급한다.
미채점이 있으면 전체 답변 정확도를 확정하지 않는다. 확인된 통과 수와 채점 완료 수를 함께 읽는다.

| 지표 | chunks/5 | pages/5 |
|---|---:|---:|
| 확인된 AI 통과 / 전체 문항 | 14/20 | 15/20 |
| 필수 근거 전체 확보 / 답변 가능 문항 | 10/16 | 12/16 |
| 근거 그룹 확보 | 33/43 | 39/43 |
| 근거 일치 AI 통과 / 내용 있는 응답 | 11/14 | 13/15 |
| 정해진 답변 보류 / 답변 불가 문항 | 4/4 | 4/4 |
| 확인된 세부 기준 충족 / 전체 기준 | 33/45 | 40/45 |
| AI 채점 완료 / 채점 가능한 응답 | 20/20 | 19/19 |
| 출력 검증 통과 응답 / 전체 문항 | 20/20 | 19/20 |
| 미생성 답변 | 0 | 0 |
| 채점 오류 / 누락 | 0 / 0 | 0 / 0 |
| 전체 실행 결과 채점 상태 | 완료(AI 기준) | 완료(AI 기준) |
| 평균 문맥 글자 수 | 3162.0 | 4159.6 |
| 평균 응답 시간(초) | 5.05 | 5.37 |
| 생성 입력 토큰(캐시 제외) | 98938 | 119142 |
| 생성 출력 토큰 | 11636 | 13226 |

## 문서 구성별 결과

통과 수는 전체 문항 기준이며, 채점 완료 수를 별도 표시한다.

| 유형 | 문항 | chunks 통과 | pages 통과 | chunks 채점 완료 | pages 채점 완료 |
|---|---:|---:|---:|---:|---:|
| multi_document | 10 | 5 | 6 | 10 | 9 |
| single_document | 6 | 5 | 5 | 6 | 6 |
| unanswerable | 4 | 4 | 4 | 4 | 4 |

## 질문 유형별 결과

통과 수는 전체 문항 기준이며, 채점 완료 수를 별도 표시한다.

| 유형 | 문항 | chunks 통과 | pages 통과 | chunks 채점 완료 | pages 채점 완료 |
|---|---:|---:|---:|---:|---:|
| boundary | 4 | 2 | 3 | 4 | 3 |
| composite | 4 | 1 | 2 | 4 | 4 |
| exception | 4 | 3 | 3 | 4 | 4 |
| timing | 4 | 4 | 3 | 4 | 4 |
| unanswerable | 4 | 4 | 4 | 4 | 4 |

두 방식 모두 채점 완료: 19/20.
pages 개선 문항: v3_d01, v3_d05.
pages 악화 문항: v3_d15.

## 실패 진단

reference_quote_missing은 정답표 인용문이 문맥에 부족하다는 뜻이며 의미상 답변 불가능 판정은 아니다.
ai_incorrect_with_complete_evidence는 생성 누락과 채점 해석 문제를 모두 검토해야 한다.

### chunks5

- v3_d01: ai_incorrect_with_complete_evidence
- v3_d04: reference_quote_missing, ai_incorrect, ai_unsupported_answer
- v3_d05: reference_quote_missing, ai_incorrect, answerable_abstention
- v3_d07: reference_quote_missing, ai_incorrect, answerable_abstention
- v3_d08: reference_quote_missing, ai_incorrect, ai_unsupported_answer
- v3_d10: reference_quote_missing
- v3_d11: reference_quote_missing, ai_incorrect, ai_unsupported_answer
- 실행 오류 단계별: {}

### pages5

- v3_d04: rag_error_or_missing
- v3_d07: reference_quote_missing, ai_incorrect
- v3_d08: reference_quote_missing, ai_incorrect
- v3_d10: reference_quote_missing
- v3_d11: reference_quote_missing, ai_incorrect, ai_unsupported_answer
- v3_d15: ai_incorrect_with_complete_evidence, ai_unsupported_answer
- 실행 오류 단계별: {"validation": 1}

## 재현과 한계

- 답변 시도와 채점 기록은 각각 40개이며, 실패 답변의 채점은 건너뛴다.
- protocol.json은 선택한 문항·원본 데이터셋 해시·PDF·코드·프롬프트·설정·최대 호출 수를 고정한다.
- attempts/의 개별 기록과 answers.json을 대조한다. 완료/오류/pending 요청을 자동 재시도하지 않는다.
- 표의 답변 보류는 출력 계약 준수 지표다. 의미상 정답 여부와 사람 검토는 별도로 판단한다.
- 검색 근거 포함은 답변 정확도가 아니다. 미채점은 정답이나 오답으로 확정하지 않는다.
- 같은 소규모 합성 문서의 단일 실행이다. 실제 기업 문서, Cloud 성능, 통계적 유의성은 검증하지 않았다.
