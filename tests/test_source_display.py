import json
from copy import deepcopy

import pymupdf

from config import DOCUMENTS_DIR, PROJECT_ROOT
from grounding import validate_answer
from source_display import excerpt_html, readable_excerpt, source_excerpts
from tests.test_grounding import response, sources


def test_all_quotes_from_reused_source_are_preserved_once_without_combining_passages():
    payload = response()
    payload["claims"][0]["evidence"].append({"source_id": "S1", "quote": "100만원 초과 부서장"})
    payload["claims"].append({"text": "초과 구간은 부서장 결재입니다.", "evidence": [
        {"source_id": "S1", "quote": "100만원 초과\n부서장"},
        {"source_id": "S1", "quote": "구매 금액 100만원 이하 팀장"},
    ]})
    result = validate_answer(json.dumps(payload), sources())
    original = deepcopy(result)
    assert source_excerpts(result, result["sources"][0]) == [
        "구매 금액\n100만원 이하 팀장", "100만원 초과 부서장",
    ]
    assert source_excerpts(result, result["sources"][1]) == ["회사 장비는 사전 검토 필요."]
    assert result == original


def test_legacy_answer_without_claims_keeps_its_original_excerpt():
    source = {"source_id": "S1", "excerpt": "기존에 검증한 원문\n발췌"}
    result = {"sources": [source]}
    original = deepcopy(result)
    assert source_excerpts(result, source) == [source["excerpt"]]
    assert result == original


def test_saved_po_answer_exposes_bank_change_rule_hidden_by_first_excerpt():
    result = json.loads((PROJECT_ROOT / "eval/results/v3_closeout_20261019/final/v3_f08.json")
                       .read_text(encoding="utf-8"))["payload"]
    original = deepcopy(result)
    source = next(s for s in result["sources"] if s["document"] == "04_contract_settlement.pdf"
                  and s["page"] == 3)
    excerpts = source_excerpts(result, source)
    assert len(excerpts) > 1
    assert "기존계좌와다르다는사유" not in "".join(source["excerpt"].split())
    combined = "".join("".join(quote.split()) for quote in excerpts)
    assert "계좌확인자료" in combined
    assert "기존계좌와다르다는사유" in combined
    assert "구매운영팀의확인기록" in combined
    assert result == original


def test_real_security_pdf_line_wraps_are_repaired_without_changing_characters():
    with pymupdf.open(DOCUMENTS_DIR / "03_it_security.pdf") as pdf:
        raw = pdf[0].get_text("text")
    assert "금\n액과" in raw and "필요\n하다" in raw and "기\n준으로" in raw
    displayed = readable_excerpt(raw)
    assert "금액과 관계없이" in displayed
    assert "보안검토가 필요하다" in displayed
    assert "공급가액 기준으로" in displayed
    assert "".join(raw.split()) == "".join(displayed.split())


def test_paragraphs_lists_explicit_spaces_and_unknown_word_boundaries_are_preserved():
    raw = "금액\n승인자\n\n1. 검토 필요\n2. 검토 불필요\n검토\n필요\n금 \n액\n100만원\n초과"
    assert readable_excerpt(raw) == raw
    assert readable_excerpt("금\r\n액과 관계없이") == "금액과 관계없이"
    assert readable_excerpt("규정\n금\n액과 관계없이") == "규정\n금액과 관계없이"


def test_display_does_not_turn_source_markup_into_html_or_change_baseline_evidence():
    raw = '<script>alert("x")</script> & [링크](https://example.com) 금\n액과'
    html = excerpt_html(raw)
    assert "<script>" not in html
    assert '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp;' in html
    assert "금액과" in html
    report = json.loads((PROJECT_ROOT / "eval/results/phase5_baseline.json").read_text(encoding="utf-8"))
    for result in report["results"]:
        for source in result["sources"]:
            assert "".join(readable_excerpt(source["excerpt"]).split()) == "".join(source["excerpt"].split())
