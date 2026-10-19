"""Framework-independent configuration; importing does not load credentials."""

from dataclasses import dataclass, field
import hashlib
import math
import os
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent
DOCUMENTS_DIR = PROJECT_ROOT / "documents"
PREVIEW_PATH = PROJECT_ROOT / "data" / "chunks_preview.json"
INDEX_DIR = PROJECT_ROOT / "data" / "chroma_db"
EMBEDDING_CACHE_DIR = PROJECT_ROOT / "data" / "embedding_models"
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_CHAT_MAX_TOKENS = 4096

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 3
MAX_QUESTION_LENGTH = 500


def pdf_fingerprints(documents_dir: Path) -> dict[str, str]:
    """Hash exactly the direct PDF inputs used by ingestion, in filename order."""
    files = sorted(path for path in documents_dir.iterdir() if path.is_file() and path.suffix.lower() == ".pdf")
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}


class ConfigurationError(ValueError):
    """Configuration needs an operator's attention; messages contain no secrets."""


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = field(default="", repr=False)
    chat_model: str = "claude-sonnet-5-5"
    chat_max_tokens: int = DEFAULT_CHAT_MAX_TOKENS
    embedding_provider: str = "fastembed"
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    embedding_dimensions: int = 384
    embedding_cache_dir: Path = EMBEDDING_CACHE_DIR
    embedding_local_files_only: bool = False
    api_timeout_seconds: float = 30.0
    chunk_size: int = CHUNK_SIZE
    chunk_overlap: int = CHUNK_OVERLAP
    top_k: int = TOP_K
    retrieval_mode: str = "chunks"
    context_max_chars: int = 6000
    langsmith_tracing: bool = False
    langsmith_api_key: str = field(default="", repr=False)
    langsmith_project: str = "enterprise-rag-mvp"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    session_question_limit: int = 10

    def __post_init__(self) -> None:
        if not self.chat_model.strip():
            raise ConfigurationError("ANTHROPIC_MODEL must not be empty.")
        if not 1 <= self.chat_max_tokens <= 4096:
            raise ConfigurationError("ANTHROPIC_MAX_TOKENS must be between 1 and 4096.")
        if self.embedding_provider != "fastembed":
            raise ConfigurationError("EMBEDDING_PROVIDER must be fastembed; Claude has no embeddings API.")
        if not self.embedding_model.strip():
            raise ConfigurationError("EMBEDDING_MODEL must not be empty.")
        if self.embedding_dimensions <= 0:
            raise ConfigurationError("EMBEDDING_DIMENSIONS must be positive.")
        if not math.isfinite(self.api_timeout_seconds) or self.api_timeout_seconds <= 0:
            raise ConfigurationError("API_TIMEOUT_SECONDS must be a finite positive number.")
        if self.chunk_size <= 0 or not 0 <= self.chunk_overlap < self.chunk_size:
            raise ConfigurationError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size.")
        if type(self.top_k) is not int or not 1 <= self.top_k <= 10:
            raise ConfigurationError("RAG_TOP_K must be an integer between 1 and 10.")
        if self.retrieval_mode not in ("chunks", "pages"):
            raise ConfigurationError("RAG_RETRIEVAL_MODE must be chunks or pages.")
        if type(self.context_max_chars) is not int or not 800 <= self.context_max_chars <= 20000:
            raise ConfigurationError("RAG_CONTEXT_MAX_CHARS must be an integer between 800 and 20000.")
        if not 1 <= self.session_question_limit <= 100:
            raise ConfigurationError("SESSION_QUESTION_LIMIT must be between 1 and 100.")

    def require_anthropic_key(self) -> str:
        if not self.anthropic_api_key.strip():
            raise ConfigurationError("Set ANTHROPIC_API_KEY in the environment or project .env file for Claude calls.")
        return self.anthropic_api_key


def load_settings(
    *,
    env_file: Path = PROJECT_ROOT / ".env",
    secrets: Mapping[str, object] | None = None,
) -> Settings:
    """Precedence: environment > supplied server secrets > local .env > defaults.

    Reading .env does not copy credentials into os.environ or log their values.
    A future Streamlit UI can supply its secrets without this module importing it.
    """
    values = dict(dotenv_values(env_file, interpolate=False)) if env_file.is_file() else {}
    values.update(secrets or {})
    names = (
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_MAX_TOKENS",
        "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS",
        "EMBEDDING_CACHE_DIR", "EMBEDDING_LOCAL_FILES_ONLY",
        "API_TIMEOUT_SECONDS", "RAG_CHUNK_SIZE", "RAG_CHUNK_OVERLAP", "RAG_TOP_K",
        "RAG_RETRIEVAL_MODE", "RAG_CONTEXT_MAX_CHARS",
        "LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT",
        "SESSION_QUESTION_LIMIT",
    )
    values.update({name: os.environ[name] for name in names if name in os.environ})

    def text(name: str, default: str) -> str:
        value = values.get(name)
        return default if value is None else str(value).strip()

    def number(name: str, default: str, converter):
        try:
            return converter(text(name, default))
        except (TypeError, ValueError):
            raise ConfigurationError(f"Invalid numeric setting: {name}.") from None

    offline = text("EMBEDDING_LOCAL_FILES_ONLY", "false").lower()
    if offline not in {"true", "false", "1", "0"}:
        raise ConfigurationError("EMBEDDING_LOCAL_FILES_ONLY must be true or false.")
    cache = text("EMBEDDING_CACHE_DIR", str(EMBEDDING_CACHE_DIR))
    if not cache:
        raise ConfigurationError("EMBEDDING_CACHE_DIR must not be empty.")
    cache_dir = Path(cache).expanduser()
    if not cache_dir.is_absolute():
        cache_dir = PROJECT_ROOT / cache_dir

    return Settings(
        anthropic_api_key=text("ANTHROPIC_API_KEY", ""),
        chat_model=text("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
        chat_max_tokens=number("ANTHROPIC_MAX_TOKENS", str(DEFAULT_CHAT_MAX_TOKENS), int),
        embedding_provider=text("EMBEDDING_PROVIDER", "fastembed"),
        embedding_model=text("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL),
        embedding_dimensions=number("EMBEDDING_DIMENSIONS", "384", int),
        embedding_cache_dir=cache_dir,
        embedding_local_files_only=offline in {"true", "1"},
        api_timeout_seconds=number("API_TIMEOUT_SECONDS", "30", float),
        chunk_size=number("RAG_CHUNK_SIZE", str(CHUNK_SIZE), int),
        chunk_overlap=number("RAG_CHUNK_OVERLAP", str(CHUNK_OVERLAP), int),
        top_k=number("RAG_TOP_K", str(TOP_K), int),
        retrieval_mode=text("RAG_RETRIEVAL_MODE", "chunks"),
        context_max_chars=number("RAG_CONTEXT_MAX_CHARS", "6000", int),
        # Optional tracing configuration must never prevent ordinary answers.
        langsmith_tracing=text("LANGSMITH_TRACING", "false").lower() in {"true", "1"},
        langsmith_api_key=text("LANGSMITH_API_KEY", ""),
        langsmith_project=text("LANGSMITH_PROJECT", "enterprise-rag-mvp"),
        langsmith_endpoint=text("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        session_question_limit=number("SESSION_QUESTION_LIMIT", "10", int),
    )
