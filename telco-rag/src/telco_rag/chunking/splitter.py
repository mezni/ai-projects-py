"""Split ingested telecom documents into overlapping chunks."""

from dataclasses import dataclass
from typing import Any

from telco_rag.ingestion.models import Document


@dataclass(frozen=True)
class Chunk:
    """A searchable passage derived from a source document."""

    chunk_id: str
    document_id: str
    title: str
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict[str, Any]
    source_path: str


def chunk_text(
    text: str,
    *,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[tuple[str, int, int]]:
    """Return (chunk text, start offset, end offset) tuples."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0:
        raise ValueError("overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    if not text.strip():
        return []

    chunks: list[tuple[str, int, int]] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Keep offsets aligned with the actual, trimmed chunk text.
        actual_start = start
        actual_end = end

        while actual_start < actual_end and text[actual_start].isspace():
            actual_start += 1

        while actual_end > actual_start and text[actual_end - 1].isspace():
            actual_end -= 1

        chunk = text[actual_start:actual_end]

        if chunk:
            chunks.append((chunk, actual_start, actual_end))

        if end == len(text):
            break

        # Advance while retaining the configured overlap.
        start = end - overlap

    return chunks


def chunk_documents(
    documents: list[Document],
    *,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[Chunk]:
    """Split documents into chunks while preserving their metadata."""
    chunks: list[Chunk] = []

    for document in documents:
        document_chunks = chunk_text(
            document.content,
            chunk_size=chunk_size,
            overlap=overlap,
        )

        for index, (text, start_char, end_char) in enumerate(document_chunks):
            chunks.append(
                Chunk(
                    chunk_id=f"{document.document_id}::chunk-{index:04d}",
                    document_id=document.document_id,
                    title=document.title,
                    text=text,
                    chunk_index=index,
                    start_char=start_char,
                    end_char=end_char,
                    metadata=dict(document.metadata),
                    source_path=document.source_path,
                )
            )

    return chunks
