"""Local multilingual embeddings. No Claude or OpenAI credentials are needed."""

import math

from langchain_core.embeddings import Embeddings
from config import ConfigurationError, DEFAULT_EMBEDDING_MODEL, Settings


class EmbeddingError(RuntimeError):
    """The local model could not be loaded or returned unusable vectors."""


def embedding_signature(settings: Settings) -> dict:
    # Prefix and implementation changes must also invalidate existing vectors.
    return {
        "provider": settings.embedding_provider,
        "model": settings.embedding_model,
        "dimensions": settings.embedding_dimensions,
        "adapter_version": 1,
    }


class LocalEmbeddings(Embeddings):
    def __init__(self, model, settings: Settings):
        self.model = model
        self.dimensions = settings.embedding_dimensions
        self.use_e5_prefixes = settings.embedding_model.startswith("intfloat/multilingual-e5")

    def _embed(self, texts: list[str], *, query: bool) -> list[list[float]]:
        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise EmbeddingError("Embedding inputs must be nonempty text.")
        try:
            if self.use_e5_prefixes:
                # E5 requires these literal prefixes even for Korean input.
                prefix = "query: " if query else "passage: "
                vectors = self.model.embed([prefix + text for text in texts], batch_size=16)
            else:
                operation = self.model.query_embed if query else self.model.passage_embed
                vectors = operation(texts, batch_size=16)
            vectors = [list(map(float, vector)) for vector in vectors]
        except Exception:
            raise EmbeddingError("Local embedding failed. Check the model cache and available memory.") from None
        if len(vectors) != len(texts):
            raise EmbeddingError("Embedding response count does not match the input count.")
        for vector in vectors:
            if len(vector) != self.dimensions or not all(math.isfinite(value) for value in vector) or not any(vector):
                raise EmbeddingError("Embedding response contains invalid vectors or dimensions.")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, query=False)

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], query=True)[0]


def create_embeddings(settings: Settings) -> LocalEmbeddings:
    # Keep model imports/downloads out of dry runs and index-reuse checks.
    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType

    if DEFAULT_EMBEDDING_MODEL not in {model["model"] for model in TextEmbedding.list_supported_models()}:
        TextEmbedding.add_custom_model(
            model=DEFAULT_EMBEDDING_MODEL, pooling=PoolingType.MEAN, normalization=True,
            sources=ModelSource(hf=DEFAULT_EMBEDDING_MODEL), dim=384,
            model_file="onnx/model.onnx", license="mit", size_in_gb=0.47,
        )
    supported = {model["model"]: model for model in TextEmbedding.list_supported_models()}
    if settings.embedding_model not in supported:
        raise ConfigurationError("EMBEDDING_MODEL is not supported by the local FastEmbed adapter.")
    if settings.embedding_dimensions != supported[settings.embedding_model]["dim"]:
        raise ConfigurationError("EMBEDDING_DIMENSIONS does not match the selected local model.")
    try:
        model = TextEmbedding(
            model_name=settings.embedding_model,
            cache_dir=str(settings.embedding_cache_dir),
            local_files_only=settings.embedding_local_files_only,
            providers=["CPUExecutionProvider"], threads=4,
        )
    except Exception:
        raise EmbeddingError(
            "Could not load the local embedding model. Check EMBEDDING_CACHE_DIR; "
            "the first run needs network access and EMBEDDING_LOCAL_FILES_ONLY=false."
        ) from None
    return LocalEmbeddings(model, settings)
