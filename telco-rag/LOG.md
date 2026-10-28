# Telco RAG — Development Log

## Project Information

- **Project:** `telco-rag`
- **Purpose:** Build a testable, secure, and observable retrieval-augmented generation system for telecom knowledge.
- **Language:** Python 3.12+
- **Package layout:** `src/telco_rag/`
- **UI:** Streamlit in `app/`
- **Dependency manager:** uv
- **Testing:** pytest
- **Code quality:** Ruff
- **Knowledge source:** Synthetic Markdown documents with YAML front matter

## Current Status

- **Last documented step:** Step 4 — Document Chunking
- **Current focus:** Fix the chunking package import and validate the test suite.
- **Known blocker:** `tests/unit/test_chunking.py` cannot import `chunk_documents` from `telco_rag.chunking`.
- **Next action:** Verify `src/telco_rag/chunking/__init__.py` exports the public functions and `src/telco_rag/chunking/splitter.py` defines them.
- **Completion policy:** Do not mark a step complete until its implementation and required checks have passed.

---

## Step 1 — Initialize Project Structure and Tooling

### Component / Step

Project foundation, package layout, and development tooling.

### Goal

Establish a reproducible Python project structure that supports incremental implementation, automated tests, and a Streamlit interface.

### Problem / Friction

Without a consistent package structure and development workflow, imports, testing, configuration, and future integration become difficult to maintain.

### Solution & Trade-offs

- Created the `telco-rag` project using uv.
- Adopted the `src/telco_rag/` package layout.
- Separated the Streamlit application into `app/`.
- Configured pytest and Ruff.
- Added environment configuration and logging setup.
- Established the initial project documentation and test structure.

**Trade-off:** The `src` layout requires correct package configuration, but it separates reusable application code from UI code and reduces accidental imports from the repository root.

### Validation

Run:

```bash
uv sync
uv run pytest
uv run ruff check .
```

**Status:** Foundation implemented; retain the latest actual test results when updating this entry.

---

## Step 2 — Create the Synthetic Telecom Knowledge Corpus

### Component / Step

Synthetic corpus and document metadata.

### Goal

Create a small, deterministic corpus that represents common telecom knowledge sources and supports ingestion and retrieval development.

### Problem / Friction

Real telecom documentation can contain confidential business information, customer information, or operationally sensitive details. It is also unsuitable as an uncontrolled dependency for early development.

### Solution & Trade-offs

Created six synthetic Markdown documents:

- `CAT-FIBER-500` — Fiber 500 service catalog
- `CAT-BIZ-1000` — Business internet catalog
- `RB-BB-001` — Broadband connectivity troubleshooting
- `RB-OPT-001` — Optical signal loss troubleshooting
- `ALARM-LOS-001` — Loss-of-signal alarm
- `SLA-BIZ-001` — Business internet SLA

Added YAML front matter containing document identity, type, version, status, access level, source type, and relevant domain metadata.

Added corpus tests to verify required documents and metadata.

**Trade-off:** Synthetic data avoids using real customer or network records, but it cannot represent every edge case found in production telecom documentation.

### Validation

Run:

```bash
uv run pytest tests/unit/test_corpus.py -v
```

**Status:** Corpus implementation established; confirm the current test result before declaring validation complete.

---

## Step 3 — Implement Document Ingestion

### Component / Step

Document parser, ingestion models, and corpus loader.

### Goal

Convert Markdown files with YAML front matter into validated Python `Document` objects.

### Problem / Friction

Retrieval requires consistent metadata and document content. Malformed front matter, missing fields, empty content, or duplicate document IDs can compromise later processing.

### Solution & Trade-offs

Implemented the ingestion design around:

- A `Document` dataclass.
- YAML front-matter parsing.
- Required metadata validation.
- Clear parsing errors.
- A loader that recursively discovers Markdown files.
- Duplicate `document_id` detection.
- Source paths relative to the corpus directory.

Added unit tests for valid documents, malformed input, required fields, empty content, corpus loading, and relative source paths.

**Trade-off:** Strict validation rejects malformed documents early. This improves reliability but requires documents to follow the established metadata contract.

### Validation

Run:

```bash
uv run python -c "from telco_rag.ingestion import load_documents; print('Ingestion import successful')"
uv run pytest tests/unit/test_ingestion.py -v
```

**Status:** Ingestion implementation established. Confirm import and test results before treating this stage as fully verified.

---

## Step 4 — Implement Document Chunking

### Component / Step

Character-based text splitter and chunk metadata.

### Goal

Split documents into smaller passages that can be embedded and retrieved independently while preserving their original source information.

### Problem / Friction

Whole documents may be too large for embedding or generation workflows. Large documents may also combine unrelated topics, making retrieval less precise.

### Solution & Trade-offs

Designed a deterministic character-based splitter with:

- Default chunk size of 500 characters.
- Default overlap of 100 characters.
- Validation of chunk size and overlap.
- Start and end character offsets.
- Stable chunk IDs derived from document IDs and chunk indexes.
- Preservation of document titles, source paths, and metadata.

Added tests for maximum chunk size, overlap, source offsets, invalid configuration, empty content, metadata preservation, unique IDs, and multiple documents.

**Trade-off:** Fixed-size character chunking is simple and deterministic, but it may split sentences or sections. Later experiments should compare character-based, token-based, and structure-aware approaches.

### Problem / Friction Encountered

The full test suite failed during test collection:

```text
ImportError: cannot import name 'chunk_documents'
from 'telco_rag.chunking'
```

Python located `src/telco_rag/chunking/__init__.py`, but the expected public function was not available through that package.

### Solution / Next Action

1. Verify `src/telco_rag/chunking/splitter.py` defines both `chunk_text` and `chunk_documents`.
2. Verify `src/telco_rag/chunking/__init__.py` exports `Chunk`, `chunk_text`, and `chunk_documents`.
3. Run the direct import check.
4. Run the chunking tests.
5. Run the full test suite and Ruff checks.
6. Record the actual result before committing.

### Validation Commands

```bash
uv run python -c "from telco_rag.chunking import chunk_documents, chunk_text; print('Chunking imports successful')"
uv run pytest tests/unit/test_chunking.py -v
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Git Commit

Only after the implementation and checks pass:

```bash
git add src/telco_rag/chunking tests/unit/test_chunking.py docs/experiments.md
git commit -m "feat(telco-rag): implement document chunking"
```

**Status:** In progress — import error must be resolved and tests rerun.

---

## Step 5 — Embedding Generation

### Component / Step

Embedding provider and batch embedding service.

### Goal

Convert document chunks and user queries into vector representations suitable for semantic search.

### Problem / Friction

Keyword search may miss relevant passages when the user and documentation use different terminology.

### Planned Solution & Trade-offs

- Define an embedding interface.
- Select and configure an embedding model.
- Generate embeddings for chunks.
- Validate vector dimensions and batch behavior.
- Handle provider errors and configuration failures.
- Add tests using deterministic test doubles where appropriate.

**Trade-off:** Hosted embedding models may provide strong semantic representations but introduce cost, network dependencies, and external data-processing considerations. Local models offer more control but require additional compute and model management.

**Status:** Planned — do not mark complete until implemented and tested.

---

## Engineering Principles

1. **Traceability:** Every retrieved chunk must be traceable to its source document.
2. **Validation:** Reject malformed inputs at pipeline boundaries.
3. **Reproducibility:** Record dependency changes, test results, and experiment configurations.
4. **Security:** Enforce authorization in the application and retrieval layers; metadata alone is not access control.
5. **Evaluation:** Compare retrieval and generation configurations using repeatable measurements.
6. **Honest status tracking:** Distinguish implemented, tested, blocked, and planned work.

---

## Log Update Template

Use this template for each subsequent step:

### Step N — Title

**Component / Step**

Name the component or workflow being changed.

**Goal**

Describe the intended outcome.

**Problem / Friction**

Describe the concrete problem being addressed and any implementation issues encountered.

**Solution & Trade-offs**

Record the implementation, important design choices, and rejected alternatives.

**Validation**

List the commands run and their actual outcomes.

**Git Commit**

Record the commit hash and message after a successful commit.

**Status**

Choose one: Planned, In Progress, Blocked, or Complete.

