"""One deliberate four-case recheck after the recorded 2,048-token truncation.

The initial run and its error stay intact. Same cases and prompt, 4,096-token
output cap, no automatic retries, no judge. Total project check: at most 6 calls.
"""
from dataclasses import replace
import hashlib
from pathlib import Path

from run import (ROOT, RecordingClaude, RAGAssistant, Retriever, answer_once,
                 hashes, load_settings, now, read, save_json, seal)
from config import DEFAULT_CHAT_MAX_TOKENS, DOCUMENTS_DIR, INDEX_DIR, pdf_fingerprints
from eval.benchmark import verify
from eval.evaluate import public_configuration
from grounding import SYSTEM_PROMPT, answer_schema

OUT = Path(__file__).resolve().parent / "recheck"


def current_hashes():
    return {**hashes(), Path(__file__).relative_to(ROOT).as_posix(): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def main():
    original = read(OUT.parent / "protocol.json")
    initial = read(OUT.parent / "answers.json")
    verify(original)
    verify(initial)
    assert initial["answer_calls"] == 2
    assert initial["results"][-1]["provider_error"]["category"] == "incomplete_response"
    assert SYSTEM_PROMPT == original["answer_prompt"]
    assert answer_schema(5) == original["answer_schema"]
    selected = original["cases"]
    assert len(selected) == 4
    folder = OUT / "attempts"
    folder.mkdir(parents=True, exist_ok=False)
    settings = replace(load_settings(), retrieval_mode="pages", top_k=5, context_max_chars=6000,
                       chat_max_tokens=DEFAULT_CHAT_MAX_TOKENS,
                       embedding_local_files_only=True, langsmith_tracing=False)
    assert settings.chat_max_tokens == 4096
    protocol = seal({
        **original, "created_at": now(), "previous_protocol_sha256": original["sha256"],
        "previous_answers_sha256": initial["sha256"], "source_sha256": current_hashes(),
        "documents_sha256": pdf_fingerprints(DOCUMENTS_DIR),
        "configuration": public_configuration(settings, read(INDEX_DIR / "manifest.json")),
        "reason": "The first timing response exhausted 2,048 output tokens. Raise the configurable default cap to 4,096; preserve the failure and deliberately recheck the same four cases once.",
        "max_answer_calls": 4, "prior_answer_calls": 2, "total_max_answer_calls": 6,
    })
    save_json(OUT / "protocol.json", protocol)
    client, retriever, results = None, None, []
    try:
        client = RecordingClaude(settings)
        retriever = Retriever(settings)
        assistant = RAGAssistant(retriever, client)
        for q in selected:
            assert current_hashes() == protocol["source_sha256"], "Code changed during execution."
            target = folder / f"{q['id']}.json"
            pending = seal({"state": "pending", "started_at": now(), "question_id": q["id"],
                            "protocol_sha256": protocol["sha256"]})
            assert not target.exists()
            save_json(target, pending)
            client.raw, client.last_usage = None, None
            before_calls = client.calls
            result = answer_once(assistant, q)
            result.update(raw_response=client.raw, answer_calls=client.calls - before_calls)
            save_json(target, seal({**pending, "state": "completed", "completed_at": now(), "payload": result}))
            results.append(result)
            print(q["id"], result["status"], "answerable=", result.get("answerable"), "calls=", client.calls, flush=True)
            if result.get("error_type") == "ClaudeError":
                break
    finally:
        if client is not None:
            client.close()
        if retriever is not None:
            retriever.close()
    assert client.calls <= 4
    save_json(OUT / "answers.json", seal({
        "created_at": now(), "protocol_sha256": protocol["sha256"],
        "status": "complete" if len(results) == 4 else "partial", "results": results,
        "answer_calls": client.calls, "judge_calls": 0, "automatic_retries": 0,
        "prior_answer_calls": initial["answer_calls"], "total_answer_calls": initial["answer_calls"] + client.calls,
        "source_unchanged": current_hashes() == protocol["source_sha256"],
        "documents_unchanged": pdf_fingerprints(DOCUMENTS_DIR) == protocol["documents_sha256"],
    }))
    return 0 if len(results) == 4 else 1


if __name__ == "__main__":
    raise SystemExit(main())
