"""One-off bounded closeout: six dev answers, then twenty final answers; no LLM judge.

Run from the repository root: python eval/results/v3_closeout_20261019/run.py dev|final
Each phase claims a new directory exclusively. Existing attempts are never repeated.
"""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from config import DOCUMENTS_DIR, INDEX_DIR, load_settings, pdf_fingerprints
from eval.benchmark import answer_once, now, read, seal, verify
from eval.evaluate import digest, public_configuration, save_json
from grounding import SYSTEM_PROMPT
from llm import ClaudeClient, ClaudeError
from rag import RAGAssistant, Retriever

OUT = Path(__file__).resolve().parent
DEV_IDS = ("v3_d01", "v3_d04", "v3_d07", "v3_d10", "v3_d11", "v3_d12")


def hashes():
    files = sorted([*ROOT.glob("*.py"), *(ROOT / "eval").glob("*.py"), *(ROOT / "tests").glob("*.py"), Path(__file__)])
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


class RecordingClaude(ClaudeClient):
    def generate(self, *args, **kwargs):
        self.raw = None
        self.calls += 1
        self.raw = super().generate(*args, **kwargs)
        return self.raw


def main():
    phase = sys.argv[1]
    if phase not in ("dev", "final"):
        raise ValueError("Choose dev or final.")
    policy = read(OUT / "review_policy.json")
    verify(policy)
    if phase == "final":
        decision = read(OUT / "dev_review.json")
        verify(decision)
        if decision.get("proceed_to_final") is not True:
            raise ValueError("Finish the source review of dev answers before final evaluation.")
    folder = OUT / phase
    folder.mkdir(exist_ok=False)
    dataset_path = ROOT / "eval/questions_v3.json"
    dataset = read(dataset_path)
    selected = [q for q in dataset if (q["id"] in DEV_IDS if phase == "dev" else q["split"] == "final")]
    assert len(selected) == (6 if phase == "dev" else 20)
    settings = replace(load_settings(), retrieval_mode="pages", top_k=5, context_max_chars=6000,
                       embedding_local_files_only=True, langsmith_tracing=False)
    protocol = seal({
        "created_at": now(), "phase": phase, "dataset": selected,
        "dataset_file_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR), "source_sha256": hashes(),
        "review_policy": policy, "answer_prompt": SYSTEM_PROMPT,
        "configuration": public_configuration(settings, read(INDEX_DIR / "manifest.json")),
        "max_answer_calls": len(selected), "max_judge_calls": 0, "automatic_retries": 0,
        "reviewer_kind": "codex_source_review_not_independent_human",
        "scope": "Same four synthetic PDFs; final scenarios held back from runtime tuning, not an external holdout.",
    })
    save_json(folder / "protocol.json", protocol)
    client = RecordingClaude(settings)
    client.calls, client.raw = 0, None
    retriever = None
    results = []
    try:
        try:
            health = client.check_connection()
        except ClaudeError as exc:
            save_json(folder / "connection.json", seal({"created_at": now(), "status": "error", **exc.diagnostic()}))
            return 1
        save_json(folder / "connection.json", seal({"created_at": now(), **health, "generation_calls": 0}))
        started = perf_counter()
        retriever = Retriever(settings)
        startup_ms = round((perf_counter() - started) * 1000, 2)
        assistant = RAGAssistant(retriever, client)
        for q in selected:
            assert hashes() == protocol["source_sha256"], "Code changed during frozen execution."
            target = folder / f"{q['id']}.json"
            pending = seal({"state": "pending", "started_at": now(), "question_id": q["id"],
                            "protocol_sha256": protocol["sha256"]})
            with target.open("x", encoding="utf-8") as handle:
                json.dump(pending, handle, ensure_ascii=False, indent=2)
            client.raw, client.last_usage = None, None
            previous = client.calls
            result = answer_once(assistant, q)
            result["raw_response"] = client.raw
            result["answer_calls"] = client.calls - previous
            result["response_sha256"] = digest(client.raw) if client.raw is not None else None
            save_json(target, seal({**pending, "state": "completed", "completed_at": now(), "payload": result}))
            results.append(result)
            print(json.dumps({"phase": phase, "id": q["id"], "status": result["status"],
                              "answerable": result.get("answerable"), "calls": client.calls,
                              "latency_ms": result["latency_ms"], "error": result.get("provider_error")}), flush=True)
            if result.get("error_type") == "ClaudeError":
                break
    finally:
        client.close()
        if retriever is not None:
            retriever.close()
    assert client.calls <= protocol["max_answer_calls"]
    save_json(folder / "answers.json", seal({
        "created_at": now(), "protocol_sha256": protocol["sha256"],
        "status": "completed" if len(results) == len(selected) else "partial",
        "results": results, "answer_calls": client.calls, "judge_calls": 0,
        "retriever_startup_ms": startup_ms,
        "source_unchanged": hashes() == protocol["source_sha256"],
        "documents_unchanged": pdf_fingerprints(DOCUMENTS_DIR) == protocol["documents_sha256"],
    }))
    return 0 if len(results) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
