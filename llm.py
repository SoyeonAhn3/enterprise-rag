"""Bounded Claude Messages API client, including JSON-schema responses.

Run ``python llm.py --check`` to verify the key and model via the Models API.
This check does not generate an answer or embed any documents.
"""

import argparse
import json
import sys

from anthropic import Anthropic, APIConnectionError, APIError, APITimeoutError, AuthenticationError, RateLimitError

from config import ConfigurationError, Settings, load_settings


class ClaudeError(RuntimeError):
    """A Claude request failed; the message contains no provider response text."""

    def __init__(self, message, *, category="provider", http_status=None):
        super().__init__(message)
        self.category = category if category in {
            "provider", "authentication", "rate_limit", "timeout", "connection",
            "api_error", "incomplete_response", "empty_response",
        } else "provider"
        self.http_status = http_status if type(http_status) is int and 100 <= http_status <= 599 else None

    def diagnostic(self):
        return {"category": self.category, "http_status": self.http_status}


class ClaudeClient:
    def __init__(self, settings: Settings, *, http_client=None):
        self.settings = settings
        self.last_usage = None
        self.client = Anthropic(
            api_key=settings.require_anthropic_key(),
            base_url="https://api.anthropic.com", timeout=settings.api_timeout_seconds,
            max_retries=0, http_client=http_client,
        )

    def _call(self, operation, **kwargs):
        try:
            return operation(**kwargs)
        except APIError as exc:
            if isinstance(exc, AuthenticationError):
                category, message = "authentication", "Claude authentication failed. Check ANTHROPIC_API_KEY."
            elif isinstance(exc, RateLimitError):
                category, message = "rate_limit", "Claude rate or usage limit reached. Check API billing and usage limits."
            elif isinstance(exc, APITimeoutError):
                category, message = "timeout", "Claude request timed out."
            elif isinstance(exc, APIConnectionError):
                category, message = "connection", "Could not connect to Claude. Check network access."
            else:
                category, message = "api_error", "Claude request failed. Check API billing, model access, and service status."
            raise ClaudeError(message, category=category, http_status=getattr(exc, "status_code", None)) from None

    def check_connection(self) -> dict:
        model = self._call(self.client.models.retrieve, model_id=self.settings.chat_model)
        return {"provider": "anthropic", "model": model.id, "status": "available"}

    def generate(self, prompt: str, *, system: str, response_schema: dict | None = None) -> str:
        self.last_usage = None
        if not isinstance(prompt, str) or not prompt.strip() or not isinstance(system, str) or not system.strip():
            raise ValueError("Claude prompt and system instruction must not be empty.")
        options = {}
        if response_schema is not None:
            options["output_config"] = {"format": {"type": "json_schema", "schema": response_schema}}
        message = self._call(
            self.client.messages.create,
            model=self.settings.chat_model, max_tokens=self.settings.chat_max_tokens,
            system=system, messages=[{"role": "user", "content": prompt}], **options,
        )
        self.last_usage = {
            key: getattr(message.usage, key, 0) or 0
            for key in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        }
        if message.stop_reason != "end_turn":
            raise ClaudeError("Claude did not return a complete text response; no answer was accepted.", category="incomplete_response")
        text = "\n".join(block.text for block in message.content if block.type == "text").strip()
        if not text:
            raise ClaudeError("Claude returned no text; no answer was accepted.", category="empty_response")
        return text

    def close(self) -> None:
        self.client.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True, help="Check key/model access without generation.")
    parser.parse_args(argv)
    client = None
    try:
        client = ClaudeClient(load_settings())
        print(json.dumps(client.check_connection(), ensure_ascii=False))
    except (ConfigurationError, ClaudeError) as exc:
        print(f"Claude check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
