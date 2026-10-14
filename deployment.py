"""Export/import a portable precomputed index; never embed PDFs at app startup.

The bundle contains only the fixed demo corpus, metadata, and precomputed vectors.
Local Chroma storage and model caches stay untracked. Import does not need a model.
"""

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from uuid import uuid4

from config import DOCUMENTS_DIR, INDEX_DIR, PROJECT_ROOT, Settings, load_settings
from index_store import (_activate_manifest, _digest, _open_client, _records_digest,
                         IndexErrorBase, index_signature, load_index)

BUNDLE_PATH = PROJECT_ROOT / "deployment" / "index_bundle.json"


def export_bundle(index_dir: Path, documents_dir: Path, settings: Settings, output: Path) -> dict:
    if output.exists():
        raise IndexErrorBase("Bundle already exists; use a new output path to preserve the previous artifact.")
    loaded = load_index(index_dir, documents_dir, settings, require_embeddings=False)
    try:
        collection = loaded.client.get_collection(loaded.manifest["collection"])
        records = collection.get(include=["documents", "metadatas", "embeddings"])
        rows = sorted([
            {"id": identity, "text": text, "metadata": metadata, "vector": [float(v) for v in vector]}
            for identity, text, metadata, vector in zip(records["ids"], records["documents"],
                                                       records["metadatas"], records["embeddings"], strict=True)
        ], key=lambda row: row["id"])
        payload = {"schema_version": 1, "signature": loaded.manifest["signature"],
                   "records_sha256": loaded.manifest["records_sha256"], "rows": rows}
        bundle = {**payload, "sha256": _digest(payload)}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
        return {"path": str(output), "chunk_count": len(rows), "bytes": output.stat().st_size, "sha256": bundle["sha256"]}
    finally:
        loaded.close()


def read_bundle(path: Path, documents_dir: Path, settings: Settings) -> dict:
    try:
        bundle = json.loads(path.read_text(encoding="utf-8"))
        payload = {key: value for key, value in bundle.items() if key != "sha256"}
        if bundle["schema_version"] != 1 or bundle["sha256"] != _digest(payload):
            raise ValueError
        if bundle["signature"] != index_signature(documents_dir, settings):
            raise ValueError
        rows = bundle["rows"]
        if not rows or len({row["id"] for row in rows}) != len(rows):
            raise ValueError
        for row in rows:
            vector = row["vector"]
            if (len(vector) != settings.embedding_dimensions
                    or any(type(value) not in (float, int) or not math.isfinite(value) for value in vector)
                    or not any(value != 0 for value in vector)):
                raise ValueError
        records = {"ids": [row["id"] for row in rows], "documents": [row["text"] for row in rows],
                   "metadatas": [row["metadata"] for row in rows]}
        if _records_digest(records) != bundle["records_sha256"]:
            raise ValueError
        return bundle
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        raise IndexErrorBase("Portable index bundle is missing, corrupt, or incompatible with the fixed corpus/settings.") from None


def ensure_index(index_dir: Path, documents_dir: Path, settings: Settings, *, bundle_path: Path = BUNDLE_PATH) -> dict:
    if (index_dir / "manifest.json").exists():
        loaded = load_index(index_dir, documents_dir, settings, require_embeddings=False)
        try:
            return {"action": "reused", "chunk_count": loaded.manifest["chunk_count"]}
        finally:
            loaded.close()
    if index_dir.exists() and any(index_dir.iterdir()):
        raise IndexErrorBase("Index directory is nonempty without a manifest; use a new directory or repair it offline.")
    bundle = read_bundle(bundle_path, documents_dir, settings)
    index_dir.mkdir(parents=True, exist_ok=True)
    client = _open_client(index_dir)
    try:
        collection_name = "enterprise_rag_" + uuid4().hex
        collection = client.create_collection(collection_name, configuration={"hnsw": {"space": "cosine"}})
        rows = bundle["rows"]
        collection.add(ids=[row["id"] for row in rows], documents=[row["text"] for row in rows],
                       metadatas=[row["metadata"] for row in rows], embeddings=[row["vector"] for row in rows])
        actual = collection.get(include=["documents", "metadatas"])
        if len(actual["ids"]) != len(rows) or _records_digest(actual) != bundle["records_sha256"]:
            raise IndexErrorBase("Imported index failed integrity verification.")
        _activate_manifest(index_dir, {
            "schema_version": 1, "collection": collection_name, "chunk_count": len(rows),
            "signature": bundle["signature"], "records_sha256": bundle["records_sha256"],
            "created_at": datetime.now(timezone.utc).isoformat(), "bundle_sha256": bundle["sha256"],
        })
        return {"action": "imported_precomputed_vectors", "chunk_count": len(rows)}
    finally:
        client.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "import", "check"])
    parser.add_argument("--bundle", type=Path, default=BUNDLE_PATH)
    parser.add_argument("--index-dir", type=Path, default=INDEX_DIR)
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        if args.action == "export":
            result = export_bundle(args.index_dir, DOCUMENTS_DIR, settings, args.bundle)
        elif args.action == "import":
            result = ensure_index(args.index_dir, DOCUMENTS_DIR, settings, bundle_path=args.bundle)
        else:
            bundle = read_bundle(args.bundle, DOCUMENTS_DIR, settings)
            result = {"status": "valid", "chunk_count": len(bundle["rows"]), "sha256": bundle["sha256"]}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (IndexErrorBase, ValueError, OSError):
        print("Deployment index check failed. Check the bundle, corpus, and settings.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
