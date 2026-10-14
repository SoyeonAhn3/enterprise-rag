"""Phase 2 real-embedding smoke check; run with python -m eval.check_retrieval.

Only question text is passed to retrieval. Evidence is inspected afterwards.
This checks q01/q07/q08, not the full ten-question RAG evaluation in Phase 5.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from config import ConfigurationError, DOCUMENTS_DIR, INDEX_DIR, PROJECT_ROOT, TOP_K, load_settings
from embeddings import EmbeddingError
from index_store import IndexErrorBase
from rag import RetrievalError, Retriever

QUESTION_IDS = ("q01", "q07", "q08")


def check_evidence(chunks: list[dict], groups: list[dict]) -> dict:
    """Report both page overlap and stricter whitespace-only quote inclusion."""
    checked = []
    for group in groups:
        page_sources = []
        quote_sources = []
        for chunk in chunks:
            candidates = [candidate for candidate in group["any_of"]
                          if candidate["document"] == chunk["source_file"] and candidate["page"] == chunk["page"]]
            if candidates:
                page_sources.append(chunk["source_id"])
            text = "".join(chunk["text"].split())
            if any("".join(candidate["quote"].split()) in text for candidate in candidates):
                quote_sources.append(chunk["source_id"])
        checked.append({"id": group["id"], "page_sources": page_sources, "quote_sources": quote_sources})
    return {
        "groups": checked,
        "page_hit_at_3": any(group["page_sources"] for group in checked),
        "all_groups_page_covered": bool(checked) and all(group["page_sources"] for group in checked),
        "all_groups_quote_covered": bool(checked) and all(group["quote_sources"] for group in checked),
    }


def run_checks(retriever: Retriever, questions: list[dict]) -> list[dict]:
    selected = {question["id"]: question for question in questions if question["id"] in QUESTION_IDS}
    if set(selected) != set(QUESTION_IDS):
        raise ValueError("The evaluation dataset must contain q01, q07, and q08.")
    results = []
    for question_id in QUESTION_IDS:
        item = selected[question_id]
        result = retriever.retrieve(item["question"])
        if len(result["retrieved_chunks"]) != TOP_K:
            raise ValueError("Retrieval did not return three chunks.")
        results.append({
            "id": question_id, **result,
            "evidence_check": check_evidence(result["retrieved_chunks"], item["evidence_groups"]),
        })
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    parser.add_argument("--documents", type=Path, default=DOCUMENTS_DIR)
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "retrieval_smoke.json")
    args = parser.parse_args(argv)
    retriever = None
    try:
        settings = load_settings()
        questions = json.loads((PROJECT_ROOT / "eval" / "questions.json").read_text(encoding="utf-8"))
        retriever = Retriever(settings, index_dir=args.index_dir, documents_dir=args.documents)
        results = run_checks(retriever, questions)
        report = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scope": "Phase 2 retrieval only; no generated answers or answer-correctness scores",
            "top_k": TOP_K,
            "index_collection": retriever.index.manifest["collection"],
            "index_signature": retriever.index.manifest["signature"],
            "results": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for result in results:
            print(json.dumps({"id": result["id"], **result["evidence_check"]}, ensure_ascii=False))
        print(f"Retrieval checks recorded at {args.output}. Review the original chunks before drawing quality conclusions.")
    except (ConfigurationError, IndexErrorBase, EmbeddingError, RetrievalError, ValueError, OSError) as exc:
        print(f"Retrieval check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if retriever is not None:
            retriever.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
