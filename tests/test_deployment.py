from copy import deepcopy
import json

import pytest

from config import DOCUMENTS_DIR, Settings
from deployment import BUNDLE_PATH, ensure_index, read_bundle
from index_store import IndexErrorBase, _digest, load_index
from tests.fakes import CountingEmbeddings


def test_portable_index_import_and_reload_need_no_model_or_document_embeddings(tmp_path, monkeypatch):
    import index_store

    monkeypatch.setattr(index_store, "create_embeddings", lambda *a: pytest.fail("model must not load"))
    settings = Settings()
    original = read_bundle(BUNDLE_PATH, DOCUMENTS_DIR, settings)
    directory = tmp_path / "chroma"
    assert ensure_index(directory, DOCUMENTS_DIR, settings)["action"] == "imported_precomputed_vectors"
    loaded = load_index(directory, DOCUMENTS_DIR, settings, require_embeddings=False)
    try:
        assert loaded.manifest["chunk_count"] == 22
        collection = loaded.client.get_collection(loaded.manifest["collection"])
        records = collection.get(include=["documents", "metadatas", "embeddings"])
        by_id = {identity: (text, meta, vector) for identity, text, meta, vector in
                 zip(records["ids"], records["documents"], records["metadatas"], records["embeddings"], strict=True)}
        for row in original["rows"]:
            text, meta, vector = by_id[row["id"]]
            assert text == row["text"] and meta == row["metadata"]
            assert list(vector) == pytest.approx(row["vector"], abs=1e-7)
    finally:
        loaded.close()
    assert ensure_index(directory, DOCUMENTS_DIR, settings)["action"] == "reused"


@pytest.mark.parametrize("change", ["hash", "model", "dimensions", "nan", "duplicate", "corpus"])
def test_corrupt_or_incompatible_bundle_is_rejected_before_database_creation(tmp_path, change):
    settings = Settings()
    bundle = deepcopy(read_bundle(BUNDLE_PATH, DOCUMENTS_DIR, settings))
    if change == "hash":
        bundle["sha256"] = "invalid"
    elif change == "model":
        bundle["signature"]["embedding"]["model"] = "different"
    elif change == "dimensions":
        bundle["rows"][0]["vector"].pop()
    elif change == "nan":
        bundle["rows"][0]["vector"][0] = float("nan")
    elif change == "duplicate":
        bundle["rows"].append(bundle["rows"][0])
    else:
        bundle["signature"]["files"]["missing.pdf"] = "fake"
    if change != "hash":
        bundle["sha256"] = _digest({key: value for key, value in bundle.items() if key != "sha256"})
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(bundle), encoding="utf-8")
    with pytest.raises(IndexErrorBase):
        ensure_index(tmp_path / "index", DOCUMENTS_DIR, settings, bundle_path=path)
    assert not (tmp_path / "index").exists()


def test_existing_nonempty_directory_is_never_overwritten(tmp_path):
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(IndexErrorBase, match="nonempty"):
        ensure_index(tmp_path, DOCUMENTS_DIR, Settings())
    assert (tmp_path / "keep.txt").read_text() == "keep"
