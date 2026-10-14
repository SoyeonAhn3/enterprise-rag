import pytest

from config import ConfigurationError, DEFAULT_EMBEDDING_MODEL, PROJECT_ROOT, Settings, load_settings
from embeddings import EmbeddingError, LocalEmbeddings, create_embeddings
from llm import ClaudeClient


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for name in (
        "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_MAX_TOKENS",
        "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "EMBEDDING_DIMENSIONS",
        "EMBEDDING_CACHE_DIR", "EMBEDDING_LOCAL_FILES_ONLY",
        "API_TIMEOUT_SECONDS", "RAG_CHUNK_SIZE", "RAG_CHUNK_OVERLAP",
    ):
        monkeypatch.delenv(name, raising=False)


def test_configuration_precedence_and_secret_representation(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("ANTHROPIC_API_KEY=file-key\nEMBEDDING_DIMENSIONS=64\n", encoding="utf-8")
    assert load_settings(env_file=path).anthropic_api_key == "file-key"
    assert load_settings(env_file=path, secrets={"ANTHROPIC_API_KEY": "server-key"}).anthropic_api_key == "server-key"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "environment-key")
    settings = load_settings(env_file=path, secrets={"ANTHROPIC_API_KEY": "server-key"})
    assert settings.anthropic_api_key == "environment-key"
    assert settings.embedding_dimensions == 64
    assert "environment-key" not in repr(settings)
    assert "anthropic_api_key" not in repr(settings)


def test_missing_claude_key_is_explicit_and_does_not_create_a_client(tmp_path):
    settings = load_settings(env_file=tmp_path / "missing")
    with pytest.raises(ConfigurationError, match="Set ANTHROPIC_API_KEY"):
        ClaudeClient(settings)


@pytest.mark.parametrize("name,value", [
    ("EMBEDDING_DIMENSIONS", "invalid-secret-value"),
    ("EMBEDDING_DIMENSIONS", "0"),
    ("API_TIMEOUT_SECONDS", "nan"),
    ("API_TIMEOUT_SECONDS", "-1"),
    ("EMBEDDING_MODEL", " "),
    ("EMBEDDING_PROVIDER", "anthropic"),
    ("EMBEDDING_CACHE_DIR", " "),
    ("EMBEDDING_LOCAL_FILES_ONLY", "invalid-secret-value"),
    ("ANTHROPIC_MODEL", " "),
    ("ANTHROPIC_MAX_TOKENS", "0"),
    ("ANTHROPIC_MAX_TOKENS", "4097"),
    ("RAG_CHUNK_OVERLAP", "800"),
])
def test_invalid_configuration_does_not_echo_values(tmp_path, monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigurationError) as caught:
        load_settings(env_file=tmp_path / "missing")
    assert "invalid-secret-value" not in str(caught.value)


def test_old_openai_configuration_cannot_be_used_as_claude_credentials(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("OPENAI_API_KEY=old-key\nOPENAI_EMBEDDING_DIMENSIONS=1536\n", encoding="utf-8")
    monkeypatch.setenv("OPENAI_API_KEY", "old-environment-key")
    settings = load_settings(env_file=path)
    assert settings.anthropic_api_key == ""
    assert settings.embedding_dimensions == 384
    assert settings.embedding_provider == "fastembed"


def test_cache_path_is_relative_to_project_and_offline_setting_is_loaded(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / ".env"
    path.write_text("EMBEDDING_CACHE_DIR=data/custom-cache\nEMBEDDING_LOCAL_FILES_ONLY=true\n", encoding="utf-8")
    settings = load_settings(env_file=path)
    assert settings.embedding_cache_dir == PROJECT_ROOT / "data/custom-cache"
    assert settings.embedding_local_files_only is True


class RecordingModel:
    def __init__(self, **kwargs):
        self.options = kwargs
        self.inputs = []

    @staticmethod
    def list_supported_models():
        return [{"model": DEFAULT_EMBEDDING_MODEL, "dim": 384}]

    def embed(self, texts, **kwargs):
        self.inputs.append(list(texts))
        return [[1.0] + [0.0] * 383 for _ in texts]


def test_local_model_needs_no_api_key_and_uses_e5_document_query_prefixes(tmp_path, monkeypatch):
    import fastembed
    monkeypatch.setattr(fastembed, "TextEmbedding", RecordingModel)
    provider = create_embeddings(Settings(embedding_cache_dir=tmp_path, embedding_local_files_only=True))
    assert len(provider.embed_documents(["문서 하나", "문서 둘"])) == 2
    assert len(provider.embed_query("질문")) == 384
    assert provider.model.inputs == [["passage: 문서 하나", "passage: 문서 둘"], ["query: 질문"]]
    assert provider.model.options["local_files_only"] is True
    assert provider.model.options["cache_dir"] == str(tmp_path)
    assert provider.model.options["providers"] == ["CPUExecutionProvider"]


@pytest.mark.parametrize("options", [{"embedding_model": "unknown-model"}, {"embedding_dimensions": 1536}])
def test_unsupported_model_or_dimensions_fail_before_loading(monkeypatch, options):
    import fastembed
    monkeypatch.setattr(fastembed, "TextEmbedding", RecordingModel)
    with pytest.raises(ConfigurationError):
        create_embeddings(Settings(**options))


def test_failed_model_load_has_actionable_error_without_raw_exception(monkeypatch):
    import fastembed

    class BrokenModel(RecordingModel):
        def __init__(self, **kwargs):
            raise OSError("unit-secret-must-not-leak")

    monkeypatch.setattr(fastembed, "TextEmbedding", BrokenModel)
    with pytest.raises(EmbeddingError, match="first run needs network") as caught:
        create_embeddings(Settings())
    assert "unit-secret-must-not-leak" not in str(caught.value)


@pytest.mark.parametrize("vectors", [[], [[1.0]], [[0.0, 0.0]], [[float('nan'), 1.0]], [[float('inf'), 1.0]]])
def test_bad_local_vectors_are_rejected(vectors):
    class BadModel:
        def embed(self, *args, **kwargs):
            return vectors

    provider = LocalEmbeddings(BadModel(), Settings(embedding_dimensions=2))
    with pytest.raises(EmbeddingError):
        provider.embed_query("hello")


def test_empty_inputs_do_not_run_inference():
    model = RecordingModel()
    provider = LocalEmbeddings(model, Settings())
    assert provider.embed_documents([]) == []
    with pytest.raises(EmbeddingError, match="nonempty"):
        provider.embed_query(" ")
    assert model.inputs == []
