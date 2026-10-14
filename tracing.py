"""Optional, bounded LangSmith tracing with explicit payloads and failure isolation.

No environment mutation or automatic tracing of credentials/constructor arguments.
One failed trace write disables this sink until its owning resource is restarted.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from config import Settings


class LangSmithTracer:
    def __init__(self, settings: Settings, *, client=None):
        self.project = settings.langsmith_project
        self.model = settings.chat_model
        self.client = None
        self.status = "disabled"
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
                    auto_batch_tracing=False, timeout_ms=(1000, 1000),
                    retry_config=Retry(total=0), omit_traced_runtime_info=True,
                )
            self.client = client
            self.status = "enabled"
        except Exception:
            self.status = "unavailable"

    def _send(self, operation, **kwargs) -> bool:
        if self.status != "enabled":
            return False
        try:
            operation(**kwargs)
            return True
        except Exception:
            # Never expose SDK exceptions, request headers, or key values.
            self.status = "unavailable"
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
                extra={"metadata": {"model": self.tracer.model, "top_k": 3}},
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
                                  trace_id=self.id, dotted_order=order,
                                  end_time=datetime.now(timezone.utc), outputs=output, error=error)

    def finish(self, result: dict):
        self.output = {key: result[key] for key in ("answer", "answerable", "sources", "latency_ms")}

    def __exit__(self, exc_type, exc, tb):
        if self.posted:
            self.tracer._send(self.tracer.client.update_run, run_id=self.id,
                              trace_id=self.id, dotted_order=self.order,
                              end_time=datetime.now(timezone.utc), outputs=getattr(self, "output", {}),
                              error=exc_type.__name__ if exc_type else None)
        return False

    def reference(self) -> dict:
        return {"status": self.tracer.status, "run_id": str(self.id) if self.posted else None}
