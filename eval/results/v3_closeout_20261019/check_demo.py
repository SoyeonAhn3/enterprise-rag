"""Replay saved live answers through the real UI; check two local server starts."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from unittest.mock import patch
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent

import streamlit as st
from streamlit.testing.v1 import AppTest
from config import load_settings
from eval.benchmark import now, read, seal, verify
from eval.evaluate import save_json
from grounding import AnswerValidationError


def check_ui():
    dev, final = read(OUT / "dev/answers.json"), read(OUT / "final/answers.json")
    verify(dev)
    verify(final)
    examples = [r for r in dev["results"] if r["id"] in ("v3_d01", "v3_d07", "v3_d10")]
    examples += [next(r for r in final["results"] if r.get("answerable") is False)]
    by_question = {r["question"]: r for r in examples}
    failure = next(r for r in dev["results"] if r["status"] == "error")
    calls, starts = [], []

    class SavedResources:
        def __init__(self, settings):
            starts.append(True)

        def answer(self, question):
            calls.append(question)
            if question == failure["question"]:
                raise AnswerValidationError(rule="quote_not_in_source")
            return by_question[question]

    settings = load_settings()
    with patch("app_runtime.AppResources", SavedResources), patch("config.load_settings", return_value=settings):
        st.cache_resource.clear()
        app = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
        assert not app.exception
        for result in examples:
            app.chat_input[0].set_value(result["question"]).run()
            assert not app.exception
            assert any(node.value == result["answer"] for node in app.markdown)
            for source in result["sources"]:
                label = f"[{source['source_id']}] {source['document']} · {source['page']}쪽"
                assert any(node.label == label for node in app.expander)
            assert app.session_state["messages"][-1]["result"] == result
        app.chat_input[0].set_value(failure["question"]).run()
        assert not app.exception and app.error
        assert "근거를 검증하지 못했습니다" in app.error[-1].value
        assert len(calls) == 5 and len(starts) == 1
        st.cache_resource.clear()
        restarted = AppTest.from_file(ROOT / "app.py", default_timeout=20).run()
        assert not restarted.exception and restarted.session_state["question_count"] == 0
        assert not restarted.chat_message
        st.cache_resource.clear()
    return {"status": "passed", "answer_ids": [r["id"] for r in examples],
            "blocked_output_id": failure["id"], "resource_initializations": len(starts),
            "source_labels_and_answer_text": "passed", "fresh_session": "passed",
            "scope": "Streamlit AppTest with saved live responses; no browser screenshot or fresh API calls."}


def check_server_starts():
    rows = []
    for attempt in (1, 2):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "RAG_RETRIEVAL_MODE": "pages", "RAG_TOP_K": "5",
               "RAG_CONTEXT_MAX_CHARS": "6000", "LANGSMITH_TRACING": "false"}
        log = OUT / f"streamlit_start_{attempt}.log"
        with log.open("w", encoding="utf-8") as handle:
            started = time.perf_counter()
            process = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true",
                "--server.address=127.0.0.1", f"--server.port={port}",
                "--browser.gatherUsageStats=false", "--server.fileWatcherType=none",
            ], cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                while time.perf_counter() - started < 30:
                    if process.poll() is not None:
                        raise RuntimeError("Local Streamlit process exited before health check.")
                    try:
                        with urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1) as response:
                            healthy = response.status == 200 and response.read() == b"ok"
                        if healthy:
                            break
                    except OSError:
                        time.sleep(0.2)
                else:
                    raise RuntimeError("Local Streamlit startup exceeded 30 seconds.")
                with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                    assert response.status == 200 and b"<html" in response.read()
                rows.append({"start": attempt, "status": "passed", "startup_ms": round((time.perf_counter()-started)*1000, 2)})
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
    return {"scope": "Local HTTP readiness only; excludes model warmup and remote Cloud deployment.", "starts": rows}


if __name__ == "__main__":
    result = seal({"created_at": now(), "ui": check_ui(), "local_server": check_server_starts(), "new_model_calls": 0})
    save_json(OUT / "demo_check.json", result)
    print(json.dumps(result, ensure_ascii=False))
