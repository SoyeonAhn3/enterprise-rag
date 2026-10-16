"""Local chunk or bounded page-context retrieval; --answer adds one Claude call."""

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import sys
import json
from time import perf_counter

from langchain_core.embeddings import Embeddings

from config import ConfigurationError, DOCUMENTS_DIR, INDEX_DIR, MAX_QUESTION_LENGTH, Settings, TOP_K, load_settings
from embeddings import EmbeddingError
from index_store import IndexErrorBase, load_index
from grounding import SYSTEM_PROMPT, AnswerValidationError, abstention, answer_schema, build_prompt, validate_answer
from llm import ClaudeClient, ClaudeError
from tracing import LangSmithTracer, generation_inputs, generation_outputs
from retrieval_context import PAGE_SELECTION_POLICY, PageContext


class RetrievalError(RuntimeError):
    """The stored index could not be searched."""


def validate_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must not be empty.")
    question = question.strip()
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Question must be at most {MAX_QUESTION_LENGTH} characters.")
    return question


@dataclass(frozen=True)
class RetrievedChunk:
    source_id: str
    source_file: str
    page: int
    chunk_id: str
    text: str
    distance: float


class Retriever:
    def __init__(
        self, settings: Settings, *, index_dir: Path = INDEX_DIR,
        documents_dir: Path = DOCUMENTS_DIR, embeddings: Embeddings | None = None,
    ):
        self.top_k = settings.top_k
        self.retrieval_mode = settings.retrieval_mode
        self.context_max_chars = settings.context_max_chars
        self.index = load_index(index_dir, documents_dir, settings, embeddings=embeddings)
        self.page_context = None
        try:
            if self.retrieval_mode == "pages":
                self.page_context = PageContext(documents_dir, self.index.manifest["signature"]["files"])
        except Exception:
            self.index.close()
            raise

    def retrieve(self, question: str) -> dict:
        question = validate_question(question)
        started = perf_counter()
        search_k = (min(self.top_k * 3, self.index.manifest["chunk_count"])
                    if self.page_context is not None else self.top_k)
        try:
            matches = self.index.store.similarity_search_with_score(question, k=search_k)
        except EmbeddingError:
            raise
        except Exception:
            raise RetrievalError("Could not search the Chroma index. Check the index and embedding configuration.") from None
        chunks = [
            RetrievedChunk(
                source_id=f"S{position}", source_file=document.metadata["source_file"],
                page=document.metadata["page"], chunk_id=document.metadata["chunk_id"],
                text=document.page_content, distance=float(distance),
            )
            for position, (document, distance) in enumerate(matches, start=1)
        ]
        ranked = [asdict(chunk) for chunk in chunks]
        context = (self.page_context.assemble(ranked, question=question,
                                             max_sources=self.top_k, max_chars=self.context_max_chars)
                   if self.page_context is not None else ranked)
        return {
            "question": question,
            "retrieved_chunks": context,
            "ranked_chunks": ranked,
            "retrieval_mode": self.retrieval_mode,
            "context_selection": PAGE_SELECTION_POLICY if self.page_context is not None else "vector_rank",
            "search_k": search_k,
            "context_chars": sum(len(chunk["text"]) for chunk in context),
            "retrieval_latency_ms": round((perf_counter() - started) * 1000, 2),
        }

    def close(self) -> None:
        self.index.close()


class RAGAssistant:
    """Reuse caller-owned retrieval and Claude clients; no retries or re-search.

    `answer()` returns a JSON-compatible result, or raises a retrieval, provider,
    or validation exception. Callers close the supplied clients when finished.
    Latency excludes client/model/index initialization and includes validation.
    """

    def __init__(self, retriever: Retriever, client: ClaudeClient, *, tracer: LangSmithTracer | None = None):
        self.retriever = retriever
        self.client = client
        self.tracer = tracer or LangSmithTracer(Settings())

    def answer(self, question: str, *, record: dict | None = None) -> dict:
        question = validate_question(question)
        started = perf_counter()
        record = record if record is not None else {}
        record.clear()
        record.update({"question": question, "retrieved_chunks": [], "stage": "retrieval"})
        trace = self.tracer.start(question)
        raw = None
        try:
            with trace:
                with trace.stage("retrieval", {"question": question}) as span:
                    retrieval = self.retriever.retrieve(question)
                    span.update(retrieval)
                record.update(retrieval)
                chunks = retrieval["retrieved_chunks"]
                record["stage"] = "prompt"
                top_k = getattr(self.retriever, "top_k", TOP_K)
                prompt = build_prompt(question, chunks, max_sources=top_k)
                generation_ms = 0.0
                if chunks:
                    record["stage"] = "generation"
                    generation_started = perf_counter()
                    try:
                        with trace.stage("generation", generation_inputs(SYSTEM_PROMPT, prompt)) as span:
                            raw = None
                            try:
                                raw = self.client.generate(prompt, system=SYSTEM_PROMPT, response_schema=answer_schema(len(chunks)))
                            finally:
                                span.update(generation_outputs(raw, getattr(self.client, "last_usage", None)))
                    finally:
                        generation_ms = round((perf_counter() - generation_started) * 1000, 2)
                        record["generation_latency_ms"] = generation_ms
                        record["token_usage"] = getattr(self.client, "last_usage", None)
                    record["stage"] = "validation"
                    grounded = validate_answer(raw, chunks, max_sources=top_k)
                else:
                    grounded = abstention()
                result = {
                    **retrieval, **grounded,
                    "retrieval_latency_ms": retrieval["retrieval_latency_ms"],
                    "generation_latency_ms": generation_ms,
                    "token_usage": record.get("token_usage"),
                    "latency_ms": round((perf_counter() - started) * 1000, 2),
                }
                trace.finish(result)
            result["latency_ms"] = round((perf_counter() - started) * 1000, 2)
            result["trace"] = trace.reference()
            record.update(result)
            record["stage"] = "complete"
            return result
        except AnswerValidationError as exc:
            record["validation_error"] = exc.diagnostic()
            if record["stage"] == "validation":
                record["response_metadata"] = {
                    "chars": len(raw) if isinstance(raw, str) else None,
                    "sha256": hashlib.sha256(raw.encode("utf-8", errors="surrogatepass")).hexdigest()
                    if isinstance(raw, str) else None,
                }
            raise
        finally:
            record["latency_ms"] = round((perf_counter() - started) * 1000, 2)
            record["trace"] = trace.reference()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--answer", action="store_true", help="Generate a grounded answer using Claude (requires API key).")
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--documents", type=Path, default=DOCUMENTS_DIR)
    args = parser.parse_args(argv)
    retriever = None
    client = None
    tracer = None
    try:
        question = validate_question(args.question)
        settings = load_settings()
        if args.answer:
            client = ClaudeClient(settings)
            tracer = LangSmithTracer(settings)
        retriever = Retriever(settings, index_dir=args.index_dir, documents_dir=args.documents)
        result = RAGAssistant(retriever, client, tracer=tracer).answer(question) if args.answer else retriever.retrieve(question)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ConfigurationError, IndexErrorBase, EmbeddingError, RetrievalError, ClaudeError,
            AnswerValidationError, ValueError, OSError) as exc:
        print(f"{'Answer' if args.answer else 'Retrieval'} failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if tracer is not None:
            tracer.close()
        if client is not None:
            client.close()
        if retriever is not None:
            retriever.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
