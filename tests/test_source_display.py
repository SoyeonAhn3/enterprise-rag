import json

import pymupdf

from config import DOCUMENTS_DIR, PROJECT_ROOT
from source_display import excerpt_html, readable_excerpt


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
