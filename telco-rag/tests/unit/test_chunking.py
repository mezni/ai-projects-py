import pytest

from telco_rag.chunking import chunk_documents, chunk_text
from telco_rag.ingestion import Document


def make_document(content: str = "A" * 1200) -> Document:
    return Document(
        document_id="RB-BB-001",
        title="Broadband Troubleshooting",
        document_type="runbook",
        content=content,
        metadata={
            "domain": "broadband",
            "access_level": "internal",
        },
        source_path="runbooks/broadband-no-connectivity.md",
    )


def test_chunk_text_respects_maximum_size() -> None:
    chunks = chunk_text("A" * 1200, chunk_size=500, overlap=100)

    assert len(chunks) == 3
    assert all(len(text) <= 500 for text, _, _ in chunks)


def test_chunk_text_preserves_overlap() -> None:
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=100)

    assert chunks[0][2] - chunks[1][1] == 100
    assert chunks[1][2] - chunks[2][1] == 100


def test_chunk_text_returns_original_offsets() -> None:
    text = "0123456789" * 100
    chunks = chunk_text(text, chunk_size=50, overlap=10)

    for chunk, start, end in chunks:
        assert chunk == text[start:end]


def test_chunk_text_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError):
        chunk_text("example", chunk_size=0)

    with pytest.raises(ValueError):
        chunk_text("example", chunk_size=10, overlap=10)

    with pytest.raises(ValueError):
        chunk_text("example", chunk_size=10, overlap=-1)


def test_chunk_text_handles_empty_content() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_documents_preserves_metadata() -> None:
    document = make_document()
    chunks = chunk_documents([document], chunk_size=500, overlap=100)

    assert len(chunks) == 3
    assert chunks[0].document_id == document.document_id
    assert chunks[0].title == document.title
    assert chunks[0].source_path == document.source_path
    assert chunks[0].metadata["domain"] == "broadband"
    assert chunks[0].metadata["access_level"] == "internal"


def test_chunk_ids_are_unique_within_document() -> None:
    chunks = chunk_documents(
        [make_document()],
        chunk_size=500,
        overlap=100,
    )

    ids = [chunk.chunk_id for chunk in chunks]

    assert len(ids) == len(set(ids))
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


def test_chunk_documents_handles_multiple_documents() -> None:
    documents = [
        make_document("A" * 600),
        Document(
            document_id="CAT-FIBER-500",
            title="Fiber 500 Service",
            document_type="product_catalog",
            content="B" * 600,
            metadata={"domain": "fiber_broadband"},
            source_path="catalog/fiber-500.md",
        ),
    ]

    chunks = chunk_documents(
        documents,
        chunk_size=500,
        overlap=100,
    )

    assert len(chunks) == 4
    assert {chunk.document_id for chunk in chunks} == {
        "RB-BB-001",
        "CAT-FIBER-500",
    }
