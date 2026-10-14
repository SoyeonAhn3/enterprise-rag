"""Local top-three retrieval; add --answer for one grounded Claude response."""

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
import sys
import json
from time import perf_counter

from langchain_core.embeddings import Embeddings

from config import ConfigurationError, DOCUMENTS_DIR, INDEX_DIR, MAX_QUESTION_LENGTH, Settings, TOP_K, load_settings
from embeddings import EmbeddingError
from index_store import IndexErrorBase, load_index
from grounding import ANSWER_SCHEMA, SYSTEM_PROMPT, AnswerValidationError, abstention, build_prompt, validate_answer
from llm import ClaudeClient, ClaudeError
from tracing import LangSmithTracer


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
        self.index = load_index(index_dir, documents_dir, settings, embeddings=embeddings)

    def retrieve(self, question: str) -> dict:
        question = validate_question(question)
        started = perf_counter()
        try:
            matches = self.index.store.similarity_search_with_score(question, k=TOP_K)
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
        return {
            "question": question,
            "retrieved_chunks": [asdict(chunk) for chunk in chunks],
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
        try:
            with trace:
                with trace.stage("retrieval", {"question": question}) as span:
                    retrieval = self.retriever.retrieve(question)
                    span.update(retrieval)
                record.update(retrieval)
                chunks = retrieval["retrieved_chunks"]
                record["stage"] = "prompt"
                prompt = build_prompt(question, chunks)
                generation_ms = 0.0
                if chunks:
                    record["stage"] = "generation"
                    generation_started = perf_counter()
                    try:
                        with trace.stage("generation", {"system": SYSTEM_PROMPT, "prompt": prompt}) as span:
                            raw = self.client.generate(prompt, system=SYSTEM_PROMPT, response_schema=ANSWER_SCHEMA)
                            span["text"] = raw
                    finally:
                        generation_ms = round((perf_counter() - generation_started) * 1000, 2)
                        record["generation_latency_ms"] = generation_ms
                    record["stage"] = "validation"
                    grounded = validate_answer(raw, chunks)
                else:
                    grounded = abstention()
                result = {
                    "question": question, **grounded, "retrieved_chunks": chunks,
                    "retrieval_latency_ms": retrieval["retrieval_latency_ms"],
                    "generation_latency_ms": generation_ms,
                    "latency_ms": round((perf_counter() - started) * 1000, 2),
                }
                trace.finish(result)
            result["latency_ms"] = round((perf_counter() - started) * 1000, 2)
            result["trace"] = trace.reference()
            record.update(result)
            record["stage"] = "complete"
            return result
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
