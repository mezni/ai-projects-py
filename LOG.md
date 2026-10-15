
# CRM Agent Development Log

## Step 1: Initialize Python Project

- **Goal:** Establish a reproducible development environment.
- **Problem:** No project structure or automated quality checks existed.
- **Solution:** Initialized Python with uv, added pytest and ruff,
  created a smoke test, and configured Git.
- **Trade-off:** Started with a single application file rather than
  introducing the full architecture immediately.
- **Code State:** Initial application and test implemented.
- **Next Step:** Connect Python to an LLM API.


## Step 2: First LLM Call

- **Goal:** Connect Python to an LLM API.
- **Problem:** The application cannot generate model responses.
- **Solution:** Added an LLM client using the OpenAI SDK and
  environment-based model configuration.
- **Trade-off:** Simple synchronous integration with one provider;
  fallback and more robust error handling are deferred.
- **Testing:** Added a mocked unit test for prompt forwarding
  and response extraction.
- **Code State:** Basic LLM integration implemented.
- **Next Step:** Structured LLM output and validation.


## Step 3: Structured LLM Output

- **Goal:** Produce predictable, validated CRM response objects.
- **Problem:** Free-form model responses are difficult to consume
  reliably in application code.
- **Solution:** Added a Pydantic response schema and used the
  LLM SDK's structured-output parsing.
- **Trade-off:** Strict schemas improve consistency but require
  schema maintenance and do not guarantee factual correctness.
- **Testing:** Added tests for valid responses, missing fields,
  and unexpected fields.
- **Code State:** Structured response schema implemented.
- **Next Step:** Prompt engineering and prompt versioning.


## Step 4: Prompt Engineering and Configuration

- **Goal:** Separate prompts and configuration from application logic.
- **Problem:** Hardcoded prompts and environment settings are difficult
  to maintain and review.
- **Solution:** Added .env configuration, a safe .env.example,
  centralized settings, external prompt files, and a few-shot example.
- **Trade-off:** External prompt files improve maintainability but
  require deployment packaging and version control.
- **Security:** Excluded .env from Git.
- **Testing:** Added prompt-loading tests.
- **Code State:** Reusable prompt configuration implemented.
- **Next Step:** CRM domain modeling.



## Step 5: CRM Domain Modeling

- **Goal:** Define typed CRM entities and their relationships.
- **Problem:** Unstructured records make validation and retrieval
  inconsistent.
- **Solution:** Created Pydantic models for customers, contracts,
  terms, add-ons, and add-on status.
- **Trade-off:** Nested models simplify the initial example, while
  a normalized database will be more suitable for larger datasets.
- **Testing:** Verified relationships, enum values, and fee validation.
- **Code State:** Domain models and synthetic sample data implemented.
- **Next Step:** Rule-based contract and add-on retrieval.
