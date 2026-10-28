"""PostgreSQL + pgvector persistence and similarity search."""

import os
from collections.abc import Callable
from typing import Any

import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from telco_rag.embeddings import EmbeddedChunk


class PostgresVectorStore:
    """Persist embedded chunks and search by cosine distance."""

    def __init__(
        self,
        dsn: str | None = None,
        dimensions: int = 1536,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")

        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise ValueError("DATABASE_URL is not configured")

        self.dimensions = dimensions
        self._connect = connect or psycopg.connect

    def _validate_vector(self, embedding: list[float]) -> None:
        if len(embedding) != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, got {len(embedding)}"
            )

    def upsert_chunks(
        self,
        embedded_chunks: list[EmbeddedChunk],
    ) -> int:
        """Insert or update chunks and their embeddings."""
        if not embedded_chunks:
            return 0

        for item in embedded_chunks:
            self._validate_vector(item.embedding)

        sql = """
            INSERT INTO document_chunks (
                chunk_id, document_id, title, content,
                chunk_index, start_char, end_char,
                metadata, source_path, embedding
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                document_id = EXCLUDED.document_id,
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                chunk_index = EXCLUDED.chunk_index,
                start_char = EXCLUDED.start_char,
                end_char = EXCLUDED.end_char,
                metadata = EXCLUDED.metadata,
                source_path = EXCLUDED.source_path,
                embedding = EXCLUDED.embedding
        """

        with self._connect(self.dsn) as connection:
            register_vector(connection)

            with connection.cursor() as cursor:
                for item in embedded_chunks:
                    chunk = item.chunk
                    cursor.execute(
                        sql,
                        (
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.title,
                            chunk.text,
                            chunk.chunk_index,
                            chunk.start_char,
                            chunk.end_char,
                            Jsonb(chunk.metadata),
                            chunk.source_path,
                            Vector(item.embedding),
                        ),
                    )

        return len(embedded_chunks)

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return the nearest chunks ordered by cosine distance."""
        self._validate_vector(query_embedding)

        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        sql = """
            SELECT
                chunk_id,
                document_id,
                title,
                content,
                metadata,
                source_path,
                (embedding <=> %s) AS distance
            FROM document_chunks
            ORDER BY embedding <=> %s
            LIMIT %s
        """

        vector = Vector(query_embedding)

        with self._connect(self.dsn) as connection:
            register_vector(connection)

            with connection.cursor() as cursor:
                cursor.execute(sql, (vector, vector, limit))
                rows = cursor.fetchall()

        columns = (
            "chunk_id",
            "document_id",
            "title",
            "content",
            "metadata",
            "source_path",
            "distance",
        )

        return [dict(zip(columns, row, strict=True)) for row in rows]
