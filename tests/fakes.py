"""Deterministic test vectors; never exposed by the application's configuration."""

import hashlib

from langchain_core.embeddings import Embeddings

from embeddings import EmbeddingError


class CountingEmbeddings(Embeddings):
    def __init__(self, dimensions=16, *, fail_documents=False, fail_query=False):
        self.dimensions = dimensions
        self.document_calls = 0
        self.document_count = 0
        self.query_calls = 0
        self.fail_documents = fail_documents
        self.fail_query = fail_query

    def vector(self, text):
        digest = hashlib.shake_256(text.encode("utf-8")).digest(self.dimensions)
        return [(value - 127.5) / 127.5 for value in digest]

    def embed_documents(self, texts):
        self.document_calls += 1
        self.document_count += len(texts)
        if self.fail_documents:
            raise EmbeddingError("Simulated provider failure.")
        return [self.vector(text) for text in texts]

    def embed_query(self, text):
        self.query_calls += 1
        if self.fail_query:
            raise EmbeddingError("Simulated provider failure.")
        return self.vector(text)
