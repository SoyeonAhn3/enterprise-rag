"""Persistent Chroma collections with an atomically activated manifest."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import tempfile
from typing import TYPE_CHECKING
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from config import Settings, pdf_fingerprints
from embeddings import create_embeddings, embedding_signature

if TYPE_CHECKING:
    from ingest import PreparedCorpus


class IndexErrorBase(RuntimeError):
    """Missing, incompatible, incomplete, or unreadable local index."""


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def index_signature(documents_dir: Path, settings: Settings) -> dict:
    files = pdf_fingerprints(documents_dir)
    if not files:
        raise IndexErrorBase("No runtime PDFs found. Check the documents directory.")
    return {
        "schema_version": 1,
        "files": files,
        "embedding": embedding_signature(settings),
        "chunking": {"size": settings.chunk_size, "overlap": settings.chunk_overlap},
        "extraction_versions": {name: version(name) for name in ("PyMuPDF", "langchain-text-splitters")},
        "distance": "cosine",
    }


def _read_manifest(index_dir: Path) -> dict:
    try:
        manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict)
                or manifest.get("schema_version") != 1
                or not re.fullmatch(r"enterprise_rag_[0-9a-f]{32}", manifest.get("collection", ""))
                or not isinstance(manifest.get("chunk_count"), int)
                or manifest["chunk_count"] <= 0
                or not isinstance(manifest.get("signature"), dict)
                or not isinstance(manifest.get("records_sha256"), str)):
            raise ValueError
        return manifest
    except (OSError, ValueError, TypeError):
        raise IndexErrorBase("Index manifest is missing or invalid. Run ingest.py --rebuild.") from None


def _records_digest(records: dict) -> str:
    rows = sorted(zip(records["ids"], records["documents"], records["metadatas"], strict=True))
    return _digest(rows)


def _open_client(index_dir: Path):
    return chromadb.PersistentClient(
        path=str(index_dir.resolve()), settings=ChromaSettings(anonymized_telemetry=False),
    )


@dataclass
class LoadedIndex:
    store: Chroma
    client: object
    manifest: dict

    def close(self) -> None:
        self.client.close()


def load_index(
    index_dir: Path, documents_dir: Path, settings: Settings, *, embeddings: Embeddings | None = None,
    require_embeddings: bool = True,
) -> LoadedIndex:
    manifest = _read_manifest(index_dir)
    if manifest["signature"] != index_signature(documents_dir, settings):
        raise IndexErrorBase("Index does not match the PDFs, embedding model, or chunk settings. Run ingest.py --rebuild.")
    if not (index_dir / "chroma.sqlite3").is_file():
        raise IndexErrorBase("Chroma storage is missing. Run ingest.py --rebuild.")
    # Index integrity is checked without embeddings or API requests.
    client = None
    try:
        client = _open_client(index_dir)
        store = Chroma(
            client=client, collection_name=manifest["collection"],
            embedding_function=embeddings, create_collection_if_not_exists=False,
        )
        records = store.get(include=["documents", "metadatas"])
        if len(records["ids"]) != manifest["chunk_count"] or _records_digest(records) != manifest["records_sha256"]:
            raise ValueError
    except Exception:
        if client is not None:
            client.close()
        raise IndexErrorBase("Chroma index is unreadable or incomplete. Run ingest.py --rebuild.") from None
    if require_embeddings and embeddings is None:
        try:
            store = Chroma(
                client=client, collection_name=manifest["collection"],
                embedding_function=create_embeddings(settings), create_collection_if_not_exists=False,
            )
        except Exception:
            client.close()
            raise
    return LoadedIndex(store, client, manifest)


def _activate_manifest(index_dir: Path, manifest: dict) -> None:
    # Replace one small closed file, never a live Chroma directory (Windows).
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=index_dir, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(manifest, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(index_dir / "manifest.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_index(
    corpus: "PreparedCorpus", index_dir: Path, documents_dir: Path, settings: Settings,
    *, rebuild: bool = False, embeddings: Embeddings | None = None,
) -> dict:
    signature = index_signature(documents_dir, settings)
    if (corpus.source_fingerprints != signature["files"]
            or corpus.chunk_size != settings.chunk_size
            or corpus.chunk_overlap != settings.chunk_overlap):
        raise IndexErrorBase("Prepared corpus does not match the current PDFs or chunk settings. Prepare it again.")
    if not rebuild and (index_dir / "manifest.json").exists():
        loaded = load_index(index_dir, documents_dir, settings, require_embeddings=False)
        try:
            return {"action": "reused", "chunk_count": loaded.manifest["chunk_count"], "collection": loaded.manifest["collection"]}
        finally:
            loaded.close()
    if not rebuild and (index_dir / "chroma.sqlite3").exists():
        raise IndexErrorBase("Existing Chroma storage has no valid manifest. Run ingest.py --rebuild.")
    if not corpus.chunks:
        raise IndexErrorBase("Cannot build an index without chunks.")

    # A failed new build never replaces the previous active collection.
    provider = embeddings if embeddings is not None else create_embeddings(settings)
    collection_name = "enterprise_rag_" + uuid4().hex
    index_dir.mkdir(parents=True, exist_ok=True)
    client = _open_client(index_dir)
    try:
        store = Chroma(
            client=client, collection_name=collection_name, embedding_function=provider,
            collection_configuration={"hnsw": {"space": "cosine"}},
        )
        store.add_documents(corpus.chunks, ids=[chunk.metadata["chunk_id"] for chunk in corpus.chunks])
        records = store.get(include=["documents", "metadatas"])
        expected = {
            "ids": [chunk.metadata["chunk_id"] for chunk in corpus.chunks],
            "documents": [chunk.page_content for chunk in corpus.chunks],
            "metadatas": [chunk.metadata for chunk in corpus.chunks],
        }
        if len(records["ids"]) != len(corpus.chunks) or _records_digest(records) != _records_digest(expected):
            raise IndexErrorBase("Stored chunks do not match the prepared corpus.")
        if signature != index_signature(documents_dir, settings):
            raise IndexErrorBase("PDFs changed during indexing. Run ingestion again.")
        manifest = {
            "schema_version": 1,
            "collection": collection_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "signature": signature,
            "chunk_count": len(corpus.chunks),
            "records_sha256": _records_digest(records),
            "library_versions": {name: version(name) for name in ("chromadb", "langchain-chroma", "fastembed", "onnxruntime")},
        }
        _activate_manifest(index_dir, manifest)
    finally:
        client.close()
    return {"action": "built", "chunk_count": len(corpus.chunks), "collection": collection_name}
