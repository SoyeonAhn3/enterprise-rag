import json

import httpx2 as httpx
import pytest

from config import Settings
from llm import ClaudeClient, ClaudeError


def message_response(*, content=None, stop_reason="end_turn"):
    return {
        "id": "msg_test", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5",
        "content": content if content is not None else [{"type": "text", "text": "확인했습니다."}],
        "stop_reason": stop_reason, "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }


def test_actual_claude_sdk_contract_uses_messages_api_and_bounded_settings():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=message_response())

    with httpx.Client(transport=httpx.MockTransport(respond), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key", chat_max_tokens=100), http_client=transport)
        try:
            assert client.generate("질문과 검색 근거", system="검색 근거만 사용하세요.") == "확인했습니다."
            assert client.client.max_retries == 0
            assert client.client.timeout == 30
        finally:
            client.close()
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.anthropic.com/v1/messages"
    assert request.headers["x-api-key"] == "unit-test-key"
    payload = json.loads(request.content)
    assert payload["model"] == "claude-sonnet-5-5"
    assert payload["max_tokens"] == 100
    assert payload["system"] == "검색 근거만 사용하세요."
    assert payload["messages"] == [{"role": "user", "content": "질문과 검색 근거"}]
    assert "temperature" not in payload


def test_connection_check_uses_models_api_without_generating_text():
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={
            "id": "claude-sonnet-5-5", "type": "model", "display_name": "Claude Sonnet 5.5",
            "created_at": "2026-09-28T00:00:00Z",
        })

    with httpx.Client(transport=httpx.MockTransport(respond), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key"), http_client=transport)
        try:
            assert client.check_connection() == {"provider": "anthropic", "model": "claude-sonnet-5-5", "status": "available"}
        finally:
            client.close()
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert str(requests[0].url) == "https://api.anthropic.com/v1/models/claude-sonnet-5-5"


@pytest.mark.parametrize("failure,expected", [
    (400, "request failed"), (401, "authentication"), (403, "model access"),
    (429, "usage limit"), (500, "request failed"), (529, "request failed"),
    ("timeout", "timed out"), ("connection", "connect"),
])
def test_claude_errors_are_bounded_and_sanitized(failure, expected):
    requests = []

    def respond(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("unit-secret-must-not-leak", request=request)
        if failure == "connection":
            raise httpx.ConnectError("unit-secret-must-not-leak", request=request)
        return httpx.Response(failure, json={"type": "error", "error": {
            "type": "api_error", "message": "unit-secret-must-not-leak",
        }})

    with httpx.Client(transport=httpx.MockTransport(respond), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key"), http_client=transport)
        try:
            with pytest.raises(ClaudeError, match=expected) as caught:
                client.generate("질문", system="한국어로 응답하세요.")
        finally:
            client.close()
    assert len(requests) == 1
    assert "unit-secret-must-not-leak" not in str(caught.value)


@pytest.mark.parametrize("reply", [
    message_response(stop_reason="max_tokens"),
    message_response(stop_reason="refusal"),
    message_response(content=[]),
    message_response(content=[{"type": "thinking", "thinking": "not user-visible", "signature": "test"}]),
])
def test_partial_refused_or_empty_outputs_are_not_successful_answers(reply):
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=reply)), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key"), http_client=transport)
        try:
            with pytest.raises(ClaudeError, match="no answer was accepted"):
                client.generate("질문", system="한국어로 응답하세요.")
        finally:
            client.close()


def test_invalid_prompt_does_not_call_the_api():
    requests = []
    with httpx.Client(transport=httpx.MockTransport(lambda request: requests.append(request)), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key"), http_client=transport)
        try:
            with pytest.raises(ValueError, match="must not be empty"):
                client.generate(" ", system="instruction")
        finally:
            client.close()
    assert not requests


def test_structured_answer_schema_is_sent_through_the_actual_sdk():
    from grounding import ANSWER_SCHEMA

    requests = []
    raw = '{"answerable":false,"claims":[]}'

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=message_response(content=[{"type": "text", "text": raw}]))

    with httpx.Client(transport=httpx.MockTransport(respond), trust_env=False) as transport:
        client = ClaudeClient(Settings(anthropic_api_key="unit-test-key"), http_client=transport)
        try:
            assert client.generate("질문", system="근거만 사용", response_schema=ANSWER_SCHEMA) == raw
        finally:
            client.close()
    assert len(requests) == 1
    payload = json.loads(requests[0].content)
    assert payload["output_config"] == {"format": {"type": "json_schema", "schema": ANSWER_SCHEMA}}
    assert "tools" not in payload
    assert "temperature" not in payload
