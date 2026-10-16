"""Optional, bounded LangSmith tracing with explicit payloads and failure isolation.

No environment mutation or automatic tracing of credentials/constructor arguments.
One failed trace write disables this sink until its owning resource is restarted.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from config import Settings
from grounding import AnswerValidationError


def generation_inputs(system: str, prompt: str) -> dict:
    return {"system": system, "prompt": prompt, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": prompt},
    ]}


def generation_outputs(text, usage) -> dict:
    """Explicit message/usage payload; never serialize a client or Settings."""
    output = {} if text is None else {
        "text": text, "choices": [{"message": {"role": "assistant", "content": text}}],
    }
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    if isinstance(usage, dict) and all(type(usage.get(k, 0)) is int and usage.get(k, 0) >= 0 for k in keys):
        counts = {k: usage.get(k, 0) for k in keys}
        # Anthropic's uncached input count excludes cache creation/read tokens.
        inputs = counts["input_tokens"] + counts["cache_creation_input_tokens"] + counts["cache_read_input_tokens"]
        output.update(token_usage=counts, usage_metadata={
            "input_tokens": inputs, "output_tokens": counts["output_tokens"],
            "total_tokens": inputs + counts["output_tokens"],
            "input_token_details": {"cache_creation": counts["cache_creation_input_tokens"],
                                    "cache_read": counts["cache_read_input_tokens"]},
        })
    return output


class LangSmithTracer:
    def __init__(self, settings: Settings, *, client=None):
        self.project = settings.langsmith_project
        self.model = settings.chat_model
        self.top_k = settings.top_k
        self.metadata = {
            "model": settings.chat_model, "ls_provider": "anthropic", "ls_model_name": settings.chat_model,
            "top_k": settings.top_k, "retrieval_mode": settings.retrieval_mode,
            "context_max_chars": settings.context_max_chars, "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap, "embedding_model": settings.embedding_model,
        }
        self.client = None
        self.status = "disabled"
        self.error_type = None
        if not settings.langsmith_tracing:
            return
        if not settings.langsmith_api_key or not self.project:
            self.status = "unconfigured"
            return
        try:
            if client is None:
                from langsmith import Client
                from urllib3.util.retry import Retry

                client = Client(
                    api_key=settings.langsmith_api_key, api_url=settings.langsmith_endpoint,
                    # Real regional requests exceeded the previous one-second
                    # limit. Keep bounded waits and zero retries, with room for
                    # ordinary network latency on both writes and readback.
                    auto_batch_tracing=False, timeout_ms=(5000, 5000),
                    retry_config=Retry(total=0), omit_traced_runtime_info=True,
                )
            self.client = client
            self.status = "enabled"
        except Exception as exc:
            self.status = "unavailable"
            self.error_type = type(exc).__name__

    def _send(self, operation, **kwargs) -> bool:
        if self.status != "enabled":
            return False
        try:
            operation(**kwargs)
            return True
        except Exception as exc:
            # Never expose SDK exceptions, request headers, or key values.
            self.status = "unavailable"
            self.error_type = type(exc).__name__
            return False

    def start(self, question: str):
        return TraceRun(self, question)

    def close(self):
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass


class TraceRun:
    def __init__(self, tracer: LangSmithTracer, question: str):
        self.tracer = tracer
        self.id = uuid4()
        self.started = datetime.now(timezone.utc)
        self.order = self.started.strftime("%Y%m%dT%H%M%S%fZ") + str(self.id)
        self.posted = False
        self.question = question

    def __enter__(self):
        if self.tracer.client is not None:
            self.posted = self.tracer._send(
                self.tracer.client.create_run, id=self.id, name="enterprise_rag", run_type="chain",
                inputs={"question": self.question}, project_name=self.tracer.project,
                start_time=self.started, trace_id=self.id, dotted_order=self.order,
                extra={"metadata": self.tracer.metadata},
            )
        return self

    @contextmanager
    def stage(self, name: str, inputs: dict):
        identity = uuid4()
        started = datetime.now(timezone.utc)
        order = self.order + "." + started.strftime("%Y%m%dT%H%M%S%fZ") + str(identity)
        posted = False
        if self.posted:
            posted = self.tracer._send(
                self.tracer.client.create_run, id=identity, name=name,
                run_type="retriever" if name == "retrieval" else "llm",
                inputs=inputs, project_name=self.tracer.project, start_time=started,
                trace_id=self.id, parent_run_id=self.id, dotted_order=order,
                extra={"metadata": self.tracer.metadata},
            )
        output = {}
        error = None
        try:
            yield output
        except BaseException as exc:
            error = type(exc).__name__
            raise
        finally:
            if posted:
                self.tracer._send(self.tracer.client.update_run, run_id=identity,
                                  trace_id=self.id, parent_run_id=self.id, dotted_order=order,
                                  end_time=datetime.now(timezone.utc), outputs=output, error=error)

    def finish(self, result: dict):
        self.output = {key: result[key] for key in ("answer", "answerable", "claims", "sources", "latency_ms",
                                                   "token_usage", "retrieval_mode", "context_chars", "search_k")
                       if key in result}

    def __exit__(self, exc_type, exc, tb):
        if self.posted:
            output = getattr(self, "output", {})
            if isinstance(exc, AnswerValidationError):
                output = {**output, "validation_error": exc.diagnostic()}
            self.tracer._send(self.tracer.client.update_run, run_id=self.id,
                              trace_id=self.id, dotted_order=self.order,
                              end_time=datetime.now(timezone.utc), outputs=output,
                              error=exc_type.__name__ if exc_type else None)
        return False

    def reference(self) -> dict:
        value = {"status": self.tracer.status, "run_id": str(self.id) if self.posted else None}
        if self.tracer.error_type:
            value["error_type"] = self.tracer.error_type
        return value
