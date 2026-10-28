# Telco RAG — Experiment History

## Purpose

This document records the experiments used to develop and evaluate `telco-rag`.

Each experiment should capture:

- **Objective:** The problem being investigated.
- **Hypothesis:** The expected outcome.
- **Configuration:** The implementation and settings being tested.
- **Validation:** The tests or measurements used to evaluate the implementation.
- **Results:** Observed outcomes, not assumed outcomes.
- **Trade-offs:** Benefits, limitations, and engineering implications.
- **Decision:** Whether to adopt, revise, or reject the approach.
- **Next steps:** Follow-up experiments or implementation work.

Experiments should be reproducible wherever possible. Record actual results after executing the relevant commands.

---

## Experiment 001 — Project Foundation and Tooling

### Objective

Establish a maintainable Python project structure for a telecom retrieval-augmented generation application.

### Problem

An inconsistent repository structure can lead to import errors, duplicated application logic, difficult testing, and configuration problems as the project grows.

### Hypothesis

A `src` package layout, a separate Streamlit application, and standardized development tools will make the codebase easier to test and extend.

### Configuration

| Setting | Choice |
|---|---|
| Project name | `telco-rag` |
| Python | 3.12+ |
| Package layout | `src/telco_rag/` |
| UI | Streamlit in `app/` |
| Dependency manager | uv |
| Testing | pytest |
| Linting and formatting | Ruff |
| Environment configuration | python-dotenv |

### Implementation

- Initialized the Python project.
- Created the reusable `telco_rag` package.
- Separated the Streamlit interface into `app/`.
- Added initial configuration and logging modules.
- Configured pytest and Ruff.
- Added environment-variable examples and Git ignore rules.
- Established the unit-test directory.

### Validation

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Results

**Status:** Foundation established; final validation status must reflect the latest local test run.

### Trade-offs

A `src` layout introduces explicit package configuration requirements. In return, it encourages proper package imports and a clearer separation between application code and user-interface code.

### Decision

Adopt the `src/telco_rag/` package layout and retain Streamlit as a separate application layer.

### Next Steps

Build the synthetic telecom knowledge corpus and establish document metadata conventions.

---

## Experiment 002 — Synthetic Telecom Knowledge Corpus

### Objective

Create a small, reproducible knowledge corpus representing common telecom documentation.

### Problem

Using real telecom documentation during early development can introduce confidentiality risks and make test results dependent on unavailable or changing source data.

### Hypothesis

A synthetic corpus with consistent metadata will support deterministic ingestion tests and later retrieval experiments without requiring real customer or operational data.

### Configuration

**Document format:** Markdown with YAML front matter.

**Initial corpus:**

| Document ID | Type | Description |
|---|---|---|
| `CAT-FIBER-500` | Product catalog | Fiber 500 service |
| `CAT-BIZ-1000` | Product catalog | Business internet service |
| `RB-BB-001` | Runbook | Broadband connectivity troubleshooting |
| `RB-OPT-001` | Runbook | Optical signal loss troubleshooting |
| `ALARM-LOS-001` | Alarm reference | Loss-of-signal alarm |
| `SLA-BIZ-001` | SLA documentation | Business internet service targets |

### Metadata Contract

The documents use these required fields:

- `document_id`
- `title`
- `document_type`
- `version`
- `status`
- `access_level`
- `source_type`

Additional metadata can describe domain, product ID, alarm code, severity, or other document-specific attributes.

### Implementation

- Created six synthetic telecom documents.
- Organized documents into catalog, runbook, alarm, and SLA directories.
- Added YAML front matter.
- Added corpus tests for expected documents and required metadata.
- Included a synthetic disclaimer for fictional SLA targets.

### Validation

```bash
uv run pytest tests/unit/test_corpus.py -v
```

### Results

**Status:** Corpus established. Confirm the latest corpus-test result before recording this experiment as fully validated.

### Trade-offs

Synthetic documents are safe and predictable for development, but they do not fully represent the language, structure, ambiguity, or complexity of production telecom knowledge.

### Decision

Use the synthetic corpus as the initial development dataset. Expand it with additional scenarios as the retrieval and evaluation pipeline matures.

### Next Steps

Implement metadata parsing, document validation, and recursive corpus loading.

---

## Experiment 003 — Document Ingestion

### Objective

Convert Markdown telecom documents into validated Python objects that downstream processing can consume consistently.

### Problem

Malformed YAML, missing metadata, empty document bodies, and duplicate document IDs can create silent inconsistencies in retrieval results.

### Hypothesis

Strict ingestion validation will catch malformed documents before they reach chunking, embedding, or storage.

### Configuration

| Component | Design |
|---|---|
| Document model | `Document` dataclass |
| Metadata format | YAML front matter |
| Parser | PyYAML |
| File encoding | UTF-8, with BOM handling |
| Corpus discovery | Recursive Markdown file loading |
| Validation | Required fields and non-empty content |
| Identity | Unique `document_id` |

### Implementation

- Added the document model.
- Implemented front-matter parsing.
- Validated required metadata fields.
- Rejected documents without a valid front-matter block.
- Rejected missing required fields and empty content.
- Added recursive corpus loading.
- Detected duplicate document IDs.
- Preserved source paths relative to the corpus directory.
- Added unit tests for valid and invalid documents.

### Validation

```bash
uv run python -c "from telco_rag.ingestion import load_documents; print('Ingestion import successful')"
uv run pytest tests/unit/test_ingestion.py -v
```

Run the complete suite after the focused tests pass:

```bash
uv run pytest
```

### Results

**Status:** Implementation established; record the actual import and test outcomes from the latest execution.

### Trade-offs

Strict validation improves data quality and makes errors easier to diagnose. It also means documents must conform to the metadata contract before they can be processed.

### Decision

Validate documents at ingestion time instead of allowing malformed records to propagate into the retrieval pipeline.

### Next Steps

Implement chunking with source offsets and metadata preservation.

---

## Experiment 004 — Character-Based Document Chunking

### Objective

Split ingested documents into passages that can be embedded and retrieved independently.

### Problem

Embedding an entire document can be inefficient and can reduce retrieval precision when the document contains multiple topics.

### Hypothesis

Fixed-size character chunks with overlap will provide a simple, deterministic baseline for retrieval experiments.

### Configuration

| Parameter | Initial value |
|---|---:|
| Chunk size | 500 characters |
| Overlap | 100 characters |
| Character unit | Python string characters |
| Chunk identity | Document ID plus chunk index |
| Source traceability | Source path and character offsets |

### Implementation

The chunking module provides:

- `Chunk`, a data model for a source passage.
- `chunk_text()`, which splits text into overlapping passages.
- `chunk_documents()`, which processes ingested documents.
- Input validation for chunk size and overlap.
- Source offsets for locating passages in original document content.
- Preservation of document IDs, titles, source paths, and metadata.
- Deterministic chunk IDs.

### Validation

```bash
uv run python -c "from telco_rag.chunking import chunk_documents, chunk_text; print('Chunking imports successful')"
uv run pytest tests/unit/test_chunking.py -v
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Observed Problem

The chunking test module failed during collection with an import error:

```text
ImportError: cannot import name 'chunk_documents'
from 'telco_rag.chunking'
```

Python located the `telco_rag.chunking` package, but the expected public function was not available from its package exports.

### Corrective Actions

1. Confirm `src/telco_rag/chunking/splitter.py` defines `chunk_text()` and `chunk_documents()`.
2. Confirm `src/telco_rag/chunking/__init__.py` imports and exports both functions.
3. Run the direct import check.
4. Run the focused chunking tests.
5. Run the full test suite and Ruff checks.
6. Record the results after execution.

### Results

**Status:** Blocked pending resolution of the import error and successful test execution.

No claim is made that the chunking tests currently pass.

### Trade-offs

Character-based chunking is simple and deterministic, but it does not account for tokenizer-specific limits and may split sentences or sections. Overlap can preserve context across boundaries, but it increases the number of chunks and therefore embedding and storage requirements.

### Decision

Retain character-based chunking as the initial baseline. Do not optimize chunk size or overlap until a retrieval evaluation dataset is available.

### Next Steps

Resolve the import error, validate chunking, and implement embedding generation.

---

## Experiment 005 — Embedding Generation

### Objective

Convert source chunks and user questions into vector representations for semantic retrieval.

### Problem

Keyword matching can fail when a question and a relevant source passage express the same concept using different terminology.

### Hypothesis

An embedding model will provide a useful semantic representation of telecom passages and queries, enabling similarity-based retrieval.

### Configuration

| Parameter | Initial choice |
|---|---|
| Provider | OpenAI API |
| Model | `text-embedding-3-small` |
| Input | Text chunks and user queries |
| Output | Floating-point vectors |
| Batch handling | Multiple texts per request |
| Test strategy | Fake client; no network calls in unit tests |

The embedding dimension must be taken from the actual model response or configured model contract. It must not be assumed by the database layer.

### Implementation

The proposed provider exposes:

- `embed_texts()` for batch embedding.
- `embed_query()` for a single user query.
- `embed_chunks()` for associating vectors with source chunks.
- `EmbeddedChunk`, which preserves the original chunk and adds its vector.
- Validation for blank input, response count, and vector dimensions.
- Dependency injection so unit tests can use a fake API client.

### Configuration and Security

The local environment configuration uses:

```dotenv
OPENAI_API_KEY=
EMBEDDING_MODEL=text-embedding-3-small
```

The API key belongs in the local `.env` file and must not be committed to Git.

### Validation

```bash
uv run pytest tests/unit/test_embeddings.py -v
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### Results

**Status:** Implementation proposed; successful test execution has not yet been confirmed.

### Trade-offs

A hosted embedding API reduces the effort needed to run an embedding model locally. However, it introduces API cost, network dependencies, service limits, and data-processing considerations.

Before embedding confidential telecom material, the organization must assess the provider, applicable data-handling requirements, and permitted content.

### Decision

Use the hosted provider as the initial implementation, with an interface that can later support alternative embedding backends.

Do not consider semantic quality validated merely because the API returns vectors.

### Next Steps

- Validate the implementation and unit tests.
- Create a labeled set of telecom questions and relevant source documents.
- Evaluate retrieval quality using consistent metrics.
- Persist vectors in PostgreSQL with pgvector.

---

## Experiment 006 — Vector Storage and Similarity Search

### Objective

Persist embedded telecom chunks and retrieve semantically relevant passages.

### Problem

In-memory vectors are not sufficient for a persistent application. The system needs durable storage, metadata filtering, and repeatable retrieval.

### Hypothesis

PostgreSQL with pgvector will provide a practical baseline for storing source text, metadata, and embeddings in one database.

### Planned Configuration

| Component | Planned approach |
|---|---|
| Database | PostgreSQL |
| Vector extension | pgvector |
| Stored content | Chunk text and source metadata |
| Vector data | Embedding vector |
| Identity | Stable chunk ID |
| Search | Vector similarity |
| Filtering | Metadata constraints, including authorization |

### Planned Validation

- Insert and retrieve a chunk.
- Verify vector dimensions.
- Verify metadata persistence.
- Test similarity ordering using known examples.
- Test empty and invalid queries.
- Verify that unauthorized content is not returned.

### Results

**Status:** Planned — no implementation results recorded.

### Trade-offs

PostgreSQL with pgvector offers relational integrity and vector search in one platform. Search performance and index selection will need to be measured as the corpus grows.

### Next Steps

Implement the database schema, persistence layer, and retrieval baseline.

---

## Experiment 007 — Retrieval Quality Baseline

### Objective

Measure whether the retrieval pipeline returns useful source passages for representative telecom questions.

### Problem

A successful database query does not guarantee that the retrieved documents are relevant or sufficient to answer a user's question.

### Hypothesis

A labeled retrieval dataset and repeatable metrics will make it possible to compare chunking, embedding, and search configurations objectively.

### Planned Dataset

Each evaluation case should include:

- A user question.
- One or more relevant document or chunk IDs.
- Optional expected answer facts.
- Optional access-control constraints.
- A category such as billing, broadband, optical alarms, product information, or SLA.

### Planned Metrics

| Metric | Purpose |
|---|---|
| Recall@k | Measures whether relevant evidence appears among the top-k results |
| Precision@k | Measures the proportion of top-k results judged relevant |
| MRR | Measures the rank of the first relevant result |
| Latency | Measures retrieval response time |
| Empty-result rate | Measures how often no results are returned |

### Results

**Status:** Planned — establish a labeled dataset before reporting metric values.

### Trade-offs

Metrics simplify comparisons but do not fully capture usefulness, operational correctness, or safety. Human review remains valuable for ambiguous telecom questions.

### Next Steps

Build a baseline evaluation dataset and compare retrieval settings.

---

## Experiment 008 — Grounded Answer Generation

### Objective

Generate answers based on retrieved telecom evidence rather than unsupported model knowledge.

### Problem

A language model may produce fluent answers that are unsupported by the available documents.

### Hypothesis

Providing retrieved passages as explicit evidence and requiring source references will improve answer traceability.

### Planned Approach

- Define a generation interface.
- Pass the user question and retrieved passages to the model.
- Require answers to distinguish evidence from uncertainty.
- Return source document and chunk identifiers.
- Handle insufficient evidence without inventing policy or network facts.
- Test unsupported questions and conflicting source passages.

### Planned Evaluation

Evaluate answer correctness, evidence support, citation accuracy, and behavior when the corpus does not contain the answer.

### Results

**Status:** Planned.

### Trade-offs

Grounding can reduce unsupported claims but does not eliminate them. The application must validate source references and evaluate the relationship between each claim and its evidence.

### Next Steps

Integrate retrieval with generation and introduce end-to-end RAG tests.

---

## Experiment 009 — Security and Access Control

### Objective

Prevent unauthorized disclosure of restricted telecom documentation.

### Problem

Documents may have different access requirements. Returning a relevant passage without checking the requester's permissions can expose sensitive information.

### Hypothesis

Authorization enforced before protected content reaches the generation layer will reduce the risk of unauthorized disclosure.

### Planned Controls

- Authenticate the requesting user.
- Resolve effective permissions from a trusted identity source.
- Apply authorization constraints during retrieval.
- Avoid relying solely on model prompts to enforce access.
- Test attempts to retrieve restricted documents.
- Treat retrieved text as untrusted input to reduce prompt-injection risk.
- Avoid logging credentials or unnecessary sensitive content.

### Planned Validation

- Authorized users can retrieve permitted documents.
- Unauthorized users cannot retrieve restricted documents.
- Requests cannot override trusted authorization rules through prompt text.
- Logs do not expose secrets.

### Results

**Status:** Planned.

### Trade-offs

Security filters add implementation and testing complexity, but they are necessary for a system intended to handle documents with different access levels.

### Next Steps

Define the authorization model and add security regression tests before exposing real protected content.

---

## Experiment 010 — Observability and Operational Reliability

### Objective

Make the RAG pipeline measurable and diagnosable.

### Problem

Without structured telemetry, it is difficult to distinguish ingestion errors, embedding failures, retrieval problems, generation failures, and latency bottlenecks.

### Hypothesis

Structured logs, request correlation, stage-level latency, and failure metrics will make debugging and operational evaluation more reliable.

### Planned Signals

- Ingestion success and failure counts.
- Number of documents and chunks processed.
- Embedding request latency and failures.
- Retrieval latency and result count.
- Generation latency and failure rate.
- End-to-end request latency.
- Evaluation scores over time.

### Planned Validation

Use deterministic tests for logging and instrumentation behavior. Ensure logs exclude secrets and unnecessary sensitive user content.

### Results

**Status:** Planned.

### Trade-offs

Observability introduces instrumentation and storage overhead. Telemetry should be proportional to operational needs and designed with privacy in mind.

### Next Steps

Instrument the ingestion, retrieval, and generation stages and establish a repeatable baseline.

---

## Experiment 011 — API and Application Integration

### Objective

Separate the reusable RAG pipeline from the user interface and provide a service boundary for future clients.

### Problem

Embedding all business logic inside a Streamlit application makes it harder to reuse, test, and deploy the pipeline independently.

### Hypothesis

A FastAPI service can expose explicit interfaces while the Streamlit application remains a separate presentation layer.

### Planned Approach

- Keep reusable logic under `src/telco_rag/`.
- Implement request and response models.
- Validate inputs at API boundaries.
- Apply authentication and authorization.
- Add integration tests.
- Connect Streamlit to the service.

### Results

**Status:** Planned.

### Trade-offs

An API boundary improves modularity and supports multiple clients, but introduces network, configuration, and deployment complexity.

### Next Steps

Implement the API after the ingestion, embedding, storage, and retrieval contracts stabilize.

---

## Experiment 012 — Deployment and Reproducibility

### Objective

Create a repeatable deployment workflow suitable for development and portfolio demonstration.

### Problem

Local-only execution can hide configuration differences and dependency problems that appear in other environments.

### Hypothesis

Containerized services, locked dependencies, automated checks, and explicit configuration will improve reproducibility.

### Planned Approach

- Pin and lock dependencies through uv.
- Add Docker configuration.
- Configure PostgreSQL with pgvector.
- Separate secrets from application configuration.
- Run automated tests in CI.
- Document startup, shutdown, and troubleshooting.

### Results

**Status:** Planned.

### Trade-offs

Containerization improves consistency but adds configuration and resource overhead. Production deployment will require additional security, backup, monitoring, and scaling decisions.

### Next Steps

Containerize the validated application components and add CI checks.

---

## Experiment Summary

| ID | Experiment | Current status |
|---|---|---|
| 001 | Project foundation and tooling | Implemented; latest validation to confirm |
| 002 | Synthetic telecom corpus | Established; latest validation to confirm |
| 003 | Document ingestion | Implemented; latest validation to confirm |
| 004 | Character-based chunking | Blocked by package import error |
| 005 | Embedding generation | Proposed; validation pending |
| 006 | Vector storage | Planned |
| 007 | Retrieval evaluation | Planned |
| 008 | Grounded answer generation | Planned |
| 009 | Security and access control | Planned |
| 010 | Observability | Planned |
| 011 | API and application integration | Planned |
| 012 | Deployment and reproducibility | Planned |

## Experiment Update Template

Use the following template when adding a new experiment.

### Experiment NNN — Title

**Objective**

What question or engineering problem is being investigated?

**Hypothesis**

What measurable outcome is expected?

**Configuration**

Record dependencies, model identifiers, parameters, dataset version, and relevant environment settings.

**Implementation**

Describe the changes made and the files affected.

**Validation**

Record the exact commands, metrics, and test scenarios used.

**Results**

Record observed results, including failures and limitations.

**Trade-offs**

Explain the benefits, costs, risks, and alternatives.

**Decision**

Adopt, revise, or reject the approach, with justification.

**Next Steps**

Identify the next experiment or implementation task.

**Git Commit**

Record the commit hash and message after a successful commit.


## Experiment 006 — Vector Storage and Similarity Search

- **Goal:** Persist telecom chunks, metadata, and embeddings.
- **Database:** PostgreSQL with pgvector.
- **Schema:** `document_chunks`.
- **Vector dimension:** 1536 for the default embedding model.
- **Similarity:** Cosine distance.
- **Implementation:** Upsert chunks and retrieve nearest neighbors.
- **Validation:** Unit tests for dimensions and query limits; database
  integration tests still required.
- **Trade-off:** Relational storage and vector search share one database,
  but schema dimensions must remain aligned with the embedding model.
- **Outcome:** Pending execution of tests and database integration checks.