"""Embedding generation using the OpenAI embeddings API."""

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from telco_rag.chunking import Chunk


@dataclass(frozen=True)
class EmbeddedChunk:
    """A chunk paired with its embedding vector."""

    chunk: Chunk
    embedding: list[float]


class OpenAIEmbeddingProvider:
    """Generate embeddings for document chunks and user queries."""

    def __init__(
        self,
        model: str | None = None,
        client: Any | None = None,
    ) -> None:
        load_dotenv()

        self.model = model or os.getenv(
            "EMBEDDING_MODEL",
            "text-embedding-3-small",
        )
        self.client = client if client is not None else OpenAI()
        self.dimensions: int | None = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of non-empty texts in input order."""
        if not texts:
            return []

        if any(not text.strip() for text in texts):
            raise ValueError("Embedding inputs must not be empty")

        response = self.client.embeddings.create(
            model=self.model,
            input=texts,
        )

        ordered_data = sorted(response.data, key=lambda item: item.index)
        vectors = [[float(value) for value in item.embedding] for item in ordered_data]

        if len(vectors) != len(texts):
            raise ValueError(
                "Embedding provider returned an unexpected number of vectors"
            )

        dimensions = len(vectors[0])

        if dimensions == 0:
            raise ValueError("Embedding vectors must not be empty")

        if any(len(vector) != dimensions for vector in vectors):
            raise ValueError("Embedding vectors have inconsistent dimensions")

        if self.dimensions is not None and dimensions != self.dimensions:
            raise ValueError(f"Expected {self.dimensions} dimensions, got {dimensions}")

        self.dimensions = dimensions
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed one user query."""
        if not query.strip():
            raise ValueError("Query must not be empty")

        return self.embed_texts([query])[0]

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[EmbeddedChunk]:
        """Embed chunks while preserving their source information."""
        if not chunks:
            return []

        vectors = self.embed_texts([chunk.text for chunk in chunks])

        return [
            EmbeddedChunk(chunk=chunk, embedding=vector)
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
