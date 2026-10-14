"""Phase 3 live answer smoke check: q01/q07/q08/q09/q10, not a correctness score.

Run with python -m eval.check_answers. This makes five billable Claude requests.
Only question text reaches RAG; reference answers/evidence stay in this checker.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from config import ConfigurationError, DOCUMENTS_DIR, INDEX_DIR, PROJECT_ROOT, TOP_K, load_settings
from embeddings import EmbeddingError
from eval.check_retrieval import check_evidence
from grounding import ABSTENTION_MESSAGE, AnswerValidationError
from index_store import IndexErrorBase
from llm import ClaudeClient, ClaudeError
from rag import RAGAssistant, RetrievalError, Retriever

QUESTION_IDS = ("q01", "q07", "q08", "q09", "q10")


def run_checks(assistant: RAGAssistant, questions: list[dict]) -> list[dict]:
    selected = {item["id"]: item for item in questions if item["id"] in QUESTION_IDS}
    if set(selected) != set(QUESTION_IDS):
        raise ValueError("The evaluation dataset must contain q01, q07, q08, q09, and q10.")
    results = []
    for identity in QUESTION_IDS:
        item = selected[identity]
        result = assistant.answer(item["question"])
        evidence = check_evidence(result["retrieved_chunks"], item["evidence_groups"])
        checks = {
            "three_chunks_retained": len(result["retrieved_chunks"]) == TOP_K,
            "answerability_matches": result["answerable"] is item["answerable"],
        }
        if item["answerable"]:
            checks["all_required_quotes_retrieved"] = evidence["all_groups_quote_covered"]
            checks["has_cited_claims"] = bool(result["claims"]) and bool(result["sources"])
        else:
            checks["fixed_abstention_without_citations"] = (
                result["answer"] == ABSTENTION_MESSAGE and not result["sources"] and not result["claims"]
            )
        results.append({
            "id": identity, **result, "retrieval_evidence_check": evidence,
            "checks": checks, "checks_passed": all(checks.values()),
            "manual_review_required": True,
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--documents", type=Path, default=DOCUMENTS_DIR)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "answer_smoke.json")
    args = parser.parse_args(argv)
    retriever = client = None
    try:
        settings = load_settings()
        questions = json.loads((PROJECT_ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
        client = ClaudeClient(settings)
        retriever = Retriever(settings, index_dir=args.index_dir, documents_dir=args.documents)
        results = run_checks(RAGAssistant(retriever, client), questions)
        report = {
            "schema_version": 1, "created_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Phase 3 five-question smoke check; semantic correctness requires manual review",
            "provider": "anthropic", "model": settings.chat_model, "top_k": TOP_K,
            "index_collection": retriever.index.manifest["collection"],
            "index_signature": retriever.index.manifest["signature"],
            "results": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for result in results:
            print(json.dumps({key: result[key] for key in ("id", "answer", "answerable", "latency_ms", "checks_passed")},
                             ensure_ascii=False), flush=True)
        print(f"Answer checks recorded at {args.output}. Review each claim against its quoted evidence.")
        return 0 if all(result["checks_passed"] for result in results) else 1
    except (ConfigurationError, IndexErrorBase, EmbeddingError, RetrievalError, ClaudeError,
            AnswerValidationError, ValueError, OSError) as exc:
        print(f"Answer check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()
        if retriever is not None:
            retriever.close()


if __name__ == "__main__":
    raise SystemExit(main())
