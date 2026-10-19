"""Final four-case check with sentence-boundary and estimate-qualifier rules.

Reuse the frozen one-shot runner, but write into a new protected directory.
Earlier truncation and content/citation findings remain part of the record.
"""
from dataclasses import replace
import hashlib
from pathlib import Path

import run as runner
from config import DEFAULT_CHAT_MAX_TOKENS, load_settings
from eval.benchmark import now, read, seal, verify
from eval.evaluate import save_json

OUT = Path(__file__).resolve().parent / "final"


def main():
    initial = read(OUT.parent / "answers.json")
    previous = read(OUT.parent / "recheck/answers.json")
    verify(initial)
    verify(previous)
    assert initial["answer_calls"] + previous["answer_calls"] == 6
    assert previous["status"] == "complete"
    assert runner.cases() == read(OUT.parent / "protocol.json")["cases"]
    OUT.mkdir(exist_ok=False)
    save_json(OUT / "plan.json", seal({
        "created_at": now(), "previous_answers_sha256": previous["sha256"],
        "initial_answers_sha256": initial["sha256"],
        "reason": "The recheck timing answer fixed legal timing but cited the security rule from the middle of a PDF-split word and omitted the non-guarantee qualifier. Add generic full-sentence and estimate-qualifier instructions, retaining the 4,096-token cap.",
        "prior_answer_calls": 6, "max_answer_calls": 4, "total_max_answer_calls": 10,
        "judge_calls": 0, "automatic_retries": 0,
        "scope": "Same four observed cases once; preserve every earlier result. No new benchmark or grader.",
    }))
    source_hashes = runner.hashes
    runner.OUT = OUT
    runner.hashes = lambda: {
        **source_hashes(),
        Path(__file__).relative_to(runner.ROOT).as_posix(): hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    runner.load_settings = lambda: replace(load_settings(), chat_max_tokens=DEFAULT_CHAT_MAX_TOKENS)
    return runner.main()


if __name__ == "__main__":
    raise SystemExit(main())
