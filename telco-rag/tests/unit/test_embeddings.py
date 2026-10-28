from types import SimpleNamespace

import pytest

from telco_rag.chunking import Chunk
from telco_rag.embeddings import OpenAIEmbeddingProvider


class FakeEmbeddingsAPI:
    """Fake embedding endpoint for tests without network calls."""

    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[dict] = []

    def create(self, *, model: str, input: list[str]):
        self.calls.append({"model": model, "input": input})

        # Reverse response order to verify that indexes are respected.
        data = [
            SimpleNamespace(index=i, embedding=vector)
            for i, vector in enumerate(self.vectors)
        ]

        return SimpleNamespace(data=list(reversed(data)))


class FakeOpenAIClient:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.embeddings = FakeEmbeddingsAPI(vectors)


def make_chunk(text: str = "Investigate broadband connectivity") -> Chunk:
    return Chunk(
        chunk_id="RB-BB-001::chunk-0000",
        document_id="RB-BB-001",
        title="Broadband Troubleshooting",
        text=text,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        metadata={"domain": "broadband", "access_level": "internal"},
        source_path="runbooks/broadband-no-connectivity.md",
    )


def test_embed_texts_returns_vectors_in_input_order() -> None:
    client = FakeOpenAIClient([[1.0, 2.0], [3.0, 4.0]])
    provider = OpenAIEmbeddingProvider(
        model="test-model",
        client=client,
    )

    vectors = provider.embed_texts(["first text", "second text"])

    assert vectors == [[1.0, 2.0], [3.0, 4.0]]
    assert client.embeddings.calls[0]["model"] == "test-model"


def test_embed_texts_returns_empty_list_for_empty_input() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([]),
    )

    assert provider.embed_texts([]) == []


def test_embed_texts_rejects_blank_input() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([]),
    )

    with pytest.raises(ValueError, match="must not be empty"):
        provider.embed_texts(["valid text", "  "])


def test_embed_query_returns_one_vector() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([[0.1, 0.2, 0.3]]),
    )

    assert provider.embed_query("Why is my internet down?") == [
        0.1,
        0.2,
        0.3,
    ]


def test_embed_query_rejects_blank_query() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([]),
    )

    with pytest.raises(ValueError, match="Query must not be empty"):
        provider.embed_query("   ")


def test_embed_chunks_preserves_chunk_metadata() -> None:
    chunk = make_chunk()
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([[0.1, 0.2, 0.3]]),
    )

    results = provider.embed_chunks([chunk])

    assert len(results) == 1
    assert results[0].chunk.chunk_id == chunk.chunk_id
    assert results[0].chunk.metadata["access_level"] == "internal"
    assert results[0].embedding == [0.1, 0.2, 0.3]


def test_embed_chunks_handles_empty_input() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([]),
    )

    assert provider.embed_chunks([]) == []


def test_embed_texts_rejects_inconsistent_vector_dimensions() -> None:
    provider = OpenAIEmbeddingProvider(
        client=FakeOpenAIClient([[1.0, 2.0], [3.0]]),
    )

    with pytest.raises(ValueError, match="inconsistent dimensions"):
        provider.embed_texts(["first", "second"])


def test_provider_rejects_dimension_changes_between_calls() -> None:
    client = FakeOpenAIClient([[1.0, 2.0]])
    provider = OpenAIEmbeddingProvider(client=client)

    provider.embed_texts(["first"])

    client.embeddings.vectors = [[1.0, 2.0, 3.0]]

    with pytest.raises(ValueError, match="Expected 2 dimensions"):
        provider.embed_texts(["second"])
