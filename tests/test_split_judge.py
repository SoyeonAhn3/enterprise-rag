from copy import deepcopy
import json

import pytest

from eval.split_judge import inputs, validate, combine, response_schema


def example():
    q = {"question": "구매 검토를 설명하세요.", "answerable": True, "expected_answer": "REFERENCE-ONLY-SECRET",
         "grading_criteria": ["CRITERION-ONLY-SECRET"], "evidence_groups": [
             {"any_of": [{"quote": "UNRETRIEVED-REFERENCE"}]}]}
    r = {"answerable": True, "answer": "예산을 검토합니다.",
         "claims": [{"text": "예산을 검토합니다.", "evidence": [{"source_id": "S1", "quote": "예산 검토 필수"}]}],
         "retrieved_chunks": [{"source_id": "S1", "text": "규정: 예산 검토 필수", "expected_answer": "ANNOTATION"}]}
    return q, r


def decision(payload):
    if "retrieved" in payload:
        return {"claim_results": [{"id": c["id"], "supported": True, "citation_complete": True,
                 "uncertain": False, "reason": "원문 근거", "evidence": deepcopy(c["evidence"]),
                 "citation_evidence": list(range(1, len(c["evidence"]) + 1))} for c in payload["claims"]], "notes": "근거 검토"}
    return {"criterion_results": [{"id": c["id"], "satisfied": True, "reason": "조건 충족", "evidence": []}
                                  for c in payload["criteria"]], "rubric_uncertain": False, "notes": "정확성 검토"}


def test_grounding_is_invariant_to_reference_answer_rubric_and_reference_passages():
    q, r = example()
    before = inputs(q, r)
    assert set(before["grounding"]) == {"question", "answerable", "answer", "claims", "retrieved"}
    assert not any(x in json.dumps(before["grounding"]) for x in ("REFERENCE", "CRITERION", "ANNOTATION"))
    assert "retrieved" not in before["correctness"]
    assert "evidence" not in before["correctness"]["claims"][0]
    q.update(expected_answer="CHANGED", answerable=False, grading_criteria=["CHANGED"], evidence_groups=[])
    after = inputs(q, r)
    assert after["grounding"] == before["grounding"]
    assert after["correctness"] != before["correctness"]
    after["grounding"]["claims"][0]["evidence"][0]["quote"] = "mutated"
    assert r["claims"][0]["evidence"][0]["quote"] == "예산 검토 필수"


@pytest.mark.parametrize("damage", ["reference", "invented_quote", "boolean", "duplicate_id", "extra_field", "empty_support", "uncited_support"])
def test_invalid_grounding_decision_cannot_be_accepted(damage):
    payload = inputs(*example())["grounding"]
    parsed = decision(payload)
    row = parsed["claim_results"][0]
    if damage == "reference": row["evidence"][0]["source_id"] = "R1"
    elif damage == "invented_quote": row["evidence"][0]["quote"] = "임의 생성 규정"
    elif damage == "boolean": row["supported"] = 1
    elif damage == "duplicate_id": parsed["claim_results"].append(deepcopy(row))
    elif damage == "extra_field": parsed["expected_answer"] = "hidden reference"
    elif damage == "empty_support": row["evidence"] = []
    else: row["citation_evidence"] = [2]
    with pytest.raises(ValueError): validate("grounding", json.dumps(parsed), payload)


def test_valid_multi_source_support_distinguishes_missing_direct_claim_citation():
    q, r = example()
    r["retrieved_chunks"].append({"source_id": "S2", "text": "견적 검토 필수"})
    r["claims"][0]["text"] = "예산과 견적을 검토합니다."
    payload = inputs(q, r)["grounding"]
    parsed = decision(payload)
    row = parsed["claim_results"][0]
    row["evidence"].append({"source_id": "S2", "quote": "견적 검토 필수"})
    row["citation_evidence"].append(2)
    with pytest.raises(ValueError, match="claim's cited"): validate("grounding", json.dumps(parsed), payload)
    row["citation_complete"] = False
    row["citation_evidence"].pop()
    assert validate("grounding", json.dumps(parsed), payload)["claim_results"][0]["supported"]
    payload["claims"][0]["evidence"].append(deepcopy(row["evidence"][-1]))
    row["citation_evidence"].append(2)
    row["citation_complete"] = True
    assert validate("grounding", json.dumps(parsed), payload) == parsed


def test_redundant_explanatory_support_does_not_expand_the_claim_citation_requirement():
    payload = inputs(*example())["grounding"]
    payload["retrieved"].append({"source_id": "S2", "text": "추가 설명: 예산 검토 필수"})
    parsed = decision(payload)
    parsed["claim_results"][0]["evidence"].append({"source_id": "S2", "quote": "예산 검토 필수"})
    accepted = validate("grounding", json.dumps(parsed), payload)
    assert accepted["claim_results"][0]["citation_complete"]
    assert accepted["claim_results"][0]["citation_evidence"] == [1]


def test_api_schema_requires_every_id_and_keyed_results_are_audited():
    for stage, payload in inputs(*example()).items():
        key = "claim_results" if stage == "grounding" else "criterion_results"
        expected = payload["claims" if stage == "grounding" else "criteria"]
        schema = response_schema(stage, payload)
        assert schema["properties"][key]["required"] == [v["id"] for v in expected]
        assert schema["properties"][key]["additionalProperties"] is False
        if stage == "grounding":
            assert schema["properties"][key]["properties"]["c1"]["properties"]["citation_evidence"]["items"]["enum"] == [1]
        parsed = decision(payload)
        parsed[key] = {v["id"]: {k: x for k, x in v.items() if k != "id"} for v in parsed[key]}
        assert validate(stage, json.dumps(parsed), payload) == decision(payload)
        parsed[key] = {}
        with pytest.raises(ValueError, match="every item"): validate(stage, json.dumps(parsed), payload)


def test_earlier_frozen_quote_schema_remains_auditable():
    from eval.split_judge import PROMPTS, EVIDENCE
    payload = inputs(*example())["grounding"]
    prompt = deepcopy(PROMPTS["grounding"])
    prompt.pop("citation_encoding")
    prompt["schema"]["properties"]["claim_results"]["items"]["properties"]["citation_evidence"] = EVIDENCE
    parsed = decision(payload)
    parsed["claim_results"][0]["citation_evidence"] = deepcopy(payload["claims"][0]["evidence"])
    assert validate("grounding", json.dumps(parsed), payload, prompt=prompt) == parsed


def test_correctness_rejects_search_evidence_and_duplicate_json_fields():
    payload = inputs(*example())["correctness"]
    parsed = decision(payload)
    parsed["criterion_results"][0]["evidence"] = [{"source_id": "S1", "quote": "예산 검토 필수"}]
    with pytest.raises(ValueError): validate("correctness", json.dumps(parsed), payload)
    with pytest.raises(ValueError, match="Duplicate"):
        validate("correctness", '{"notes":"x","notes":"y"}', payload)


def test_abstention_correctness_is_separate_from_supported_claims_and_uncertainty():
    q, r = example()
    r.update(answerable=False, answer="보류", claims=[])
    payloads = inputs(q, r)
    stages = {s: {"status": "success", "input": p, "decision": validate(s, json.dumps(decision(p)), p)} for s, p in payloads.items()}
    combined = combine(stages)
    assert combined == {"accurate": False, "grounded": True, "citation_complete": True, "uncertain": False, "overall_pass": False}
    stages["correctness"]["decision"]["rubric_uncertain"] = True
    assert combine(stages)["overall_pass"] is None
    stages["grounding"] = {"status": "error"}
    assert combine(stages)["grounded"] is None
    assert combine(stages)["overall_pass"] is None
