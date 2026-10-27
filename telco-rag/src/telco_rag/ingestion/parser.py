"""Parse Markdown documents with YAML front matter."""

from pathlib import Path
from typing import Any

import yaml

from telco_rag.ingestion.models import Document

REQUIRED_FIELDS = (
    "document_id",
    "title",
    "document_type",
    "version",
    "status",
    "access_level",
    "source_type",
)


class DocumentParseError(ValueError):
    """Raised when a source document is invalid."""


def parse_document(text: str, source_path: str = "") -> Document:
    """Parse and validate a Markdown document."""
    if text.startswith("\ufeff"):
        text = text.removeprefix("\ufeff")

    if not text.startswith("---\n"):
        raise DocumentParseError(
            f"{source_path}: document must start with YAML front matter"
        )

    lines = text.splitlines()
    closing_index = next(
        (index for index in range(1, len(lines)) if lines[index] == "---"),
        None,
    )

    if closing_index is None:
        raise DocumentParseError(
            f"{source_path}: missing closing front matter delimiter"
        )

    metadata = yaml.safe_load("\n".join(lines[1:closing_index]))

    if not isinstance(metadata, dict):
        raise DocumentParseError(f"{source_path}: front matter must be a YAML mapping")

    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in metadata
        or not isinstance(metadata[field], str)
        or not metadata[field].strip()
    ]
    if missing:
        raise DocumentParseError(
            f"{source_path}: missing or invalid required fields: {', '.join(missing)}"
        )

    content = "\n".join(lines[closing_index + 1 :]).strip()
    if not content:
        raise DocumentParseError(f"{source_path}: document content cannot be empty")

    document_id = metadata["document_id"].strip()
    title = metadata["title"].strip()
    document_type = metadata["document_type"].strip()

    extra_metadata: dict[str, Any] = {
        key: value
        for key, value in metadata.items()
        if key not in {"document_id", "title", "document_type"}
    }

    return Document(
        document_id=document_id,
        title=title,
        document_type=document_type,
        content=content + "\n",
        metadata=extra_metadata,
        source_path=source_path,
    )


def parse_document_file(path: Path, base_dir: Path) -> Document:
    """Read and parse one document, preserving its relative source path."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DocumentParseError(f"{path}: unable to read document: {exc}") from exc

    try:
        source_path = path.relative_to(base_dir).as_posix()
    except ValueError as exc:
        raise DocumentParseError(
            f"{path}: document is outside the corpus directory"
        ) from exc

    try:
        return parse_document(text, source_path)
    except yaml.YAMLError as exc:
        raise DocumentParseError(
            f"{source_path}: invalid YAML front matter: {exc}"
        ) from exc
