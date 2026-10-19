from dataclasses import replace
from copy import deepcopy
import json

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import app_runtime
import config
from config import ConfigurationError, PROJECT_ROOT, Settings
from grounding import ABSTENTION_MESSAGE
from llm import ClaudeError
from tests.test_answers import FakeClaude, FakeRetriever
from tests.test_grounding import response
from rag import RAGAssistant


@pytest.fixture
def ui(monkeypatch):
    st.cache_resource.clear()
    calls = {"created": 0, "questions": [], "error": None}

    class Resources:
        def __init__(self, settings):
            calls["created"] += 1

        def answer(self, question):
            calls["questions"].append(question)
            if calls["error"]:
                raise calls["error"]
            if "식당" in question:
                return {"answer": ABSTENTION_MESSAGE, "answerable": False,
                        "sources": [], "latency_ms": 1.0}
            return RAGAssistant(FakeRetriever(), FakeClaude()).answer(question)

    monkeypatch.setattr(app_runtime, "AppResources", Resources)
    monkeypatch.setattr(config, "load_settings", lambda **k: Settings(anthropic_api_key="test-server-key"))
    app = AppTest.from_file(PROJECT_ROOT / "app.py", default_timeout=15).run()
    assert not app.exception
    yield app, calls
    st.cache_resource.clear()


def test_chat_examples_sources_and_cached_resources_across_reruns(ui):
    app, calls = ui
    app.button[0].click().run()
    assert not app.exception
    assert len(app.chat_message) == 2
    assert any("approval.pdf · 2쪽" in expander.label for expander in app.expander)
    assert any("100만원 이하 팀장" in node.proto.body for node in app.get("html"))
    app.chat_input[0].set_value("다른 업무 질문").run()
    assert not app.exception
    assert calls["created"] == 1
    assert len(calls["questions"]) == 2
    assert len(app.chat_message) == 4
    assert not app.text_input  # No visitor API-key entry.


def test_unanswerable_question_has_no_source_expanders(ui):
    app, calls = ui
    app.chat_input[0].set_value("직원 식당의 채식 메뉴는?").run()
    assert not app.exception
    assert any(ABSTENTION_MESSAGE == node.value for node in app.markdown)
    assert not any(".pdf" in expander.label for expander in app.expander)


@pytest.mark.parametrize("error", [ClaudeError("sensitive-key"), ConfigurationError("sensitive-key")])
def test_api_or_configuration_failure_is_safe_and_consumes_an_attempt(ui, error):
    app, calls = ui
    calls["error"] = error
    app.chat_input[0].set_value("질문").run()
    assert not app.exception
    assert app.error
    assert all("sensitive-key" not in node.value for node in app.error)
    assert app.session_state["question_count"] == 1
    assert len(calls["questions"]) == 1


def test_session_limit_blocks_example_and_free_text_without_new_calls(ui):
    app, calls = ui
    app.session_state["question_count"] = 10
    app.run()
    assert app.button[0].disabled
    assert app.chat_input[0].disabled
    assert app.warning
    assert not calls["questions"]


def test_blank_or_overlong_input_is_rejected_before_api_usage(ui):
    app, calls = ui
    app.chat_input[0].set_value("  ").run()
    assert not calls["questions"]
    app.chat_input[0].set_value("가" * 501).run()
    assert not calls["questions"]
    assert app.session_state["question_count"] == 0


def test_real_pdf_split_word_is_repaired_in_existing_chat_without_changing_evidence(ui):
    app, calls = ui
    report = json.loads((PROJECT_ROOT / "eval/results/phase5_baseline.json").read_text(encoding="utf-8"))
    result = next(item for item in report["results"] if item["id"] == "q07")
    original = deepcopy(result)
    assert any("금\n액과" in source["excerpt"] for source in result["sources"])
    app.session_state["messages"] = [{"question": result["question"], "result": result}]
    app.run()
    assert not app.exception
    assert any("계약은 금액과 관계없이" in node.proto.body for node in app.get("html"))
    assert all("금\n액과" not in node.proto.body for node in app.get("html"))
    assert app.session_state["messages"][0]["result"] == original
    assert not calls["questions"]  # Reformatting old chat incurs no model call.


def test_reused_source_displays_all_distinct_quotes_in_one_expander_without_new_calls(ui):
    app, calls = ui
    payload = response()
    payload["claims"][0]["evidence"].append({"source_id": "S1", "quote": "100만원 초과 부서장"})
    payload["claims"].append({"text": "초과 금액에는 부서장 결재가 필요합니다.",
                              "evidence": [{"source_id": "S1", "quote": "100만원 초과 부서장"}]})
    result = RAGAssistant(FakeRetriever(), FakeClaude(json.dumps(payload))).answer("결재 구간은?")
    original = deepcopy(result)
    app.session_state["messages"] = [{"question": result["question"], "result": result}]
    app.run()
    assert not app.exception
    expanders = [e for e in app.expander if "approval.pdf · 2쪽" in e.label]
    assert len(expanders) == 1
    rendered = expanders[0].get("html")
    assert len(rendered) == 2
    assert "100만원 이하 팀장" in rendered[0].proto.body
    assert "100만원 초과 부서장" in rendered[1].proto.body
    assert [c.value for c in expanders[0].caption] == ["인용 1", "인용 2"]
    assert app.session_state["messages"][0]["result"] == original
    assert not calls["questions"]
