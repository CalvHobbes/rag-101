# RAG Architecture

This document defines the **architecture, principles, and phased design**
for a **production-grade Retrieval-Augmented Generation (RAG) system**.

It is intended to be a **living system blueprint**, not a tutorial or a demo.
The focus is on **correctness, inspectability, and long-term maintainability**.

---

## Table of Contents
- [System Architecture Diagram](#system-architecture-diagram)
- [1. Core Principles](#1-core-principles)
- [2. RAG System Phases](#2-rag-system-phases-high-level)
- [3. Ingestion](#3-ingestion)
- [4. Retrieval](#4-retrieval)
- [5. Generation](#5-generation)
- [6. Citation & Grounding](#6-citation--grounding)
- [7. Evaluation](#7-evaluation)
- [8. Serving / APIs](#8-serving--apis)
- [9. Observability & Cost Tracking](#9-observability--cost-tracking)
- [10. Maintenance & Re-indexing](#10-maintenance--re-indexing)
- [11. Error Handling & Resilience](#11-error-handling--resilience)
- [12. Durable Workflows](#12-durable-workflows-deferred)
- [13. Guiding Philosophy](#13-guiding-philosophy)

---

## System Architecture Diagram

![RAG System Architecture](gemini%20rag%20101%20architecture%20image.png)

### Flow Summary

| Phase | Input | Output | Key Components |
|-------|-------|--------|----------------|
| **Ingestion** | Raw documents | Stored vectors + metadata | Loader → Normalizer → Chunker → Embedder |
| **Retrieval** | User query | Ranked chunks | Query embed → Similarity search → Re-rank |
| **Generation** | Query + Context | LLM response | Prompt assembly → LLM call → Parse |
| **Citation** | Response + Sources | Grounded answer | Attribution → Hallucination check |

---

## 1. Core Principles

These principles are non-negotiable and apply to all phases of the system.

### 1.1 Minimize Stack Complexity
- Prefer fewer, stable components
- Every additional tool increases operational and cognitive overhead
- Introduce new systems only when scale or requirements force it

---

### 1.2 Own the Architecture
- Frameworks are **utilities**, not architectural owners
- Core data flow, state, and lifecycle must live in first-party code
- Any framework must be replaceable without rewriting the system

---

### 1.3 Strict Separation of Concerns
Each RAG phase is a **distinct system**:

- Ingestion
- Retrieval
- Generation
- Evaluation
- Serving
- Observability

No phase should leak responsibilities into another.

---

### 1.4 Prefer Unified, Durable Storage
- Fewer databases are better than many specialized ones
- Prefer storage that supports:
  - durability
  - backups
  - SQL inspection
  - metadata and vectors together

---

### 1.5 Make Everything Inspectable
You must be able to answer:
- What data was ingested?
- How was it chunked?
- Which model embedded it?
- Where is it stored?

If you can’t inspect a step, you can’t trust it.

---

### 1.6 Delay Automation & Orchestration
- No file watchers
- No schedulers
- No workflow engines
- Deterministic ingestion runs first; automation later

---

## 2. RAG System Phases (High Level)

1. Ingestion
2. Retrieval
3. Generation
4. Citation & Grounding
5. Evaluation
6. Serving / APIs
7. Observability & Cost Tracking
8. Maintenance & Re-indexing
9. Error Handling & Resilience
10. Durable Workflows

---

## 3. Ingestion

### 3.1 Purpose of Ingestion

Ingestion converts **raw documents** into **durable, retrievable knowledge units**.

Its output is:
- text chunks
- rich metadata
- vector embeddings
- persisted storage

Ingestion does **not**:
- generate answers
- rank results
- evaluate quality

---

## 3.2 Ingestion Tasks & Implementation Choices

### Task 1: File Discovery & State Tracking

**Goal:**  
Detect which files should be ingested and avoid reprocessing unchanged files.

**Tasks:**
- Traverse a specified folder
- Compute a stable hash per file
- Compare against ingestion history

**Implementation:**
- Language: Python
- Hashing: `hashlib` (SHA256 preferred)
- State storage: Postgres table (same database as chunks/vectors)

**Data Stored:**
- file_path
- file_hash
- ingested_at
- embedding_model

---

### Task 2: Document Loading

**Goal:**  
Extract text while preserving structural metadata (page numbers, source).

**Tasks:**
- Load PDFs page-by-page
- Load plain text files
- Attach source metadata

**Framework / Classes:**
- LangChain loaders:
  - `PyMuPDFLoader` (fitz) - **Selected for PDF**
  - `TextLoader`

**Why PyMuPDFLoader?**
- **vs PyPDFLoader (pypdf):** PyMuPDF correctly handles complex kerning and layout-preserving spacing where `pypdf` often inserts incorrect spaces (e.g., "P r e - C h u n k").
- **vs Docling:** While `Docling` is powerful for deep layout analysis, it is significantly heavier (~70x slower in our benchmarks) and adds complex dependencies. `PyMuPDF` provides the sweet spot of speed (<1s/file) and text extraction accuracy for standard RAG ingestion.

**Output:**
- `Document` objects with:
  - `page_content`
  - `metadata.source`
  - `metadata.page` (for PDFs)

---

### Task 3: Text Normalization

**Goal:**  
Clean text before chunking to improve embedding quality.

**Tasks:**
- Remove null characters
- Collapse excessive newlines
- Strip leading/trailing whitespace

**Implementation:**
- Plain Python functions
- No framework dependency

**Important:**
- Normalization must occur **before chunking**
- Never embed uncleaned text

---

### Task 4: Chunking

**Goal:**  
Split text into deterministic, semantically meaningful chunks.

**Tasks:**
- Chunk text with overlap
- Preserve metadata per chunk
- Generate stable chunk IDs

**Framework / Classes:**
- LangChain:
  - `RecursiveCharacterTextSplitter`

**Recommended Parameters:**
- `chunk_size`: 700–900 characters
- `chunk_overlap`: 100–200 characters

**Chunk Metadata Must Include:**
- source
- page
- chunk_id

---

### Task 5: Metadata Enrichment

**Goal:**  
Enable traceability, citations, and debugging.

**Tasks:**
- Attach ingestion metadata to every chunk
- Keep metadata flat and queryable

**Recommended Metadata Fields:**
- source
- page
- chunk_id
- file_hash
- ingestion_version
- embedding_model
- created_at

---

### Task 6: Embedding Generation (Learning-Friendly)

**Goal:**  
Convert text chunks into vector representations.

**Tasks:**
- Embed chunks using a cost-effective model
- Explicitly version the embedding model
- Isolate embedding logic behind a single interface

**Framework / Classes:**
- LangChain embeddings:
  - `OpenAIEmbeddings`
  - `HuggingFaceEmbeddings` (local)

**Recommended Models (Learning Mode):**
- `text-embedding-3-small`
- `sentence-transformers/all-MiniLM-L6-v2`
- `bge-small-en`

**Important:**
- Embedding logic must be swappable
- Store embedding model name and vector dimension
- Never mix embedding models in the same index without versioning

---

### Task 7: Vector + Metadata Storage

**Goal:**  
Persist embeddings and metadata durably and inspectably.

**Recommended Storage:**
- Postgres + pgvector

**Why:**
- One database for vectors and metadata
- SQL debugging and inspection
- Mature operational tooling

**Stored Per Chunk:**
- chunk text
- embedding vector
- embedding dimension
- metadata fields
- ingestion timestamps

---

### Task 8: Idempotency & Re-runs

**Goal:**  
Ensure ingestion can be safely re-run.

**Tasks:**
- Skip unchanged files
- Avoid duplicate chunks
- Preserve ingestion history

**Mechanisms:**
- File hashing
- Unique constraints
- Explicit ingestion versions

---

## 3.3 Ingestion Guarantees

At the end of ingestion:

- Every vector maps to a known source
- Every chunk is traceable to a file and page
- Every embedding is reproducible
- Storage can be queried directly with SQL

---

## 4. Retrieval

### 4.1 Purpose of Retrieval

Retrieval converts a **user query** into a **ranked set of relevant chunks**.

Its output is:
- ordered list of chunks
- similarity scores
- source metadata for citation

Retrieval does **not**:
- generate answers
- modify stored data
- make decisions about response format

---

### 4.2 Retrieval Tasks & Implementation Choices

### Task 1: Query Preprocessing

**Goal:**  
Normalize and optionally expand the user query before embedding.

**Tasks:**
- Clean query text (trim, normalize whitespace)
- Optionally expand query with synonyms or reformulations
- Log original and processed query for debugging

**Implementation:**
- Plain Python functions
- No framework dependency for basic normalization
- Optional: LLM-based query expansion (defer until needed)

---

### Task 2: Query Embedding

**Goal:**  
Convert the user query into a vector using the **same model** as ingestion.

**Tasks:**
- Embed query text
- Validate embedding dimension matches stored vectors
- Handle API errors gracefully

**Framework / Classes:**
- Same embedding interface used in ingestion
- LangChain: `OpenAIEmbeddings`, `HuggingFaceEmbeddings`

**Critical:**
- Query embedding model **must match** document embedding model
- Never mix embedding models without explicit versioning

---

### Task 3: Similarity Search

**Goal:**  
Find the top-k most similar chunks to the query vector.

**Tasks:**
- Execute vector similarity query
- Return chunks with scores
- Apply distance threshold if configured

**Implementation:**
- Postgres + pgvector: `<=>` (cosine), `<->` (L2), `<#>` (inner product)
- Direct SQL for transparency and control

**Recommended Parameters:**
- `top_k`: 5–10 for most use cases
- `distance_threshold`: optional, model-dependent

**Output:**
- List of (chunk, score, metadata) tuples

---

### Task 4: Metadata Filtering

**Goal:**  
Apply filters to narrow retrieval scope before or after similarity search.

**Tasks:**
- Filter by source file, date range, or custom tags
- Support both pre-filter (SQL WHERE) and post-filter approaches

**Implementation:**
- Pre-filter: Add WHERE clauses to pgvector query
- Post-filter: Filter results in Python after retrieval

**Trade-offs:**
- Pre-filter: More efficient, but requires indexed metadata columns
- Post-filter: Simpler, but may waste compute on irrelevant chunks

---

### Task 5: Re-ranking (Optional)

**Goal:**  
Improve retrieval quality by re-scoring results with a more expensive model.

**Tasks:**
- Take top-k results from initial retrieval
- Score each (query, chunk) pair with a cross-encoder
- Re-order by cross-encoder score

**Framework / Classes:**
- `sentence-transformers` CrossEncoder
- Cohere Rerank API
- LangChain: `CohereRerank`

**When to Add:**
- Only after measuring retrieval quality
- Adds latency and cost
- Defer until baseline retrieval is proven insufficient

---

### 4.3 Retrieval Guarantees

At the end of retrieval:
- Every returned chunk is traceable to its source
- Similarity scores are interpretable
- Query and results are logged for debugging
- No answer generation has occurred

---

## 5. Generation

### 5.1 Purpose of Generation

Generation converts **retrieved context + user query** into a **natural language answer**.

Its output is:
- synthesized answer text
- (optionally) structured response with citations

Generation does **not**:
- retrieve documents
- persist state
- evaluate answer quality

---

### 5.2 Generation Tasks & Implementation Choices

### Task 1: Context Assembly

**Goal:**  
Combine retrieved chunks into a coherent context window.

**Tasks:**
- Order chunks by relevance score
- Truncate to fit model context limits
- Preserve source attribution markers

**Implementation:**
- Plain Python string formatting
- Track token count to avoid context overflow
- Format: chunk text + source marker (e.g., `[Source: file.pdf, p.3]`)

**Important:**
- Never exceed model context window
- Prioritize higher-scored chunks
- Maintain chunk boundaries for citation

---

### Task 2: Prompt Template Design

**Goal:**  
Create consistent, debuggable prompts.

**Tasks:**
- Define system prompt (role, constraints)
- Define user prompt (query + context)
- Keep templates versioned and inspectable

**Implementation:**
- Plain Python f-strings or template files
- Avoid framework-specific prompt abstractions
- Store templates in version control

**Recommended Structure:**
```
System: You are a helpful assistant. Answer based only on the provided context.
        If the context doesn't contain the answer, say "I don't know."

Context:
{assembled_context}

Question: {user_query}

Answer:
```

---

### Task 3: LLM Invocation

**Goal:**  
Call the LLM with the assembled prompt.

**Tasks:**
- Send prompt to LLM API
- Handle rate limits and errors
- Capture response and token usage

**Framework / Classes:**
- Native SDKs preferred: `openai`, `google-generativeai`, `anthropic`
- LangChain `ChatOpenAI` acceptable for model switching

**Important:**
- Log full request/response for debugging
- Track token counts for cost monitoring
- Use structured outputs when available (JSON mode)

---

### Task 4: Response Parsing

**Goal:**  
Extract and validate the answer from LLM output.

**Tasks:**
- Parse raw response text
- Extract citations if structured output used
- Validate response format

**Implementation:**
- Plain Python parsing
- Pydantic models for structured responses
- Handle malformed responses gracefully

---

### 5.3 Generation Guarantees

At the end of generation:
- Answer is derived only from provided context
- Token usage is tracked
- Full prompt and response are logged
- No external data sources were accessed

---

## 6. Citation & Grounding

### 6.1 Purpose of Citation & Grounding

Ensure answers are **traceable to sources** and **factually grounded** in retrieved content.

Its output is:
- answer with inline or footnote citations
- grounding confidence indicators

Citation does **not**:
- generate new content
- modify source data
- replace evaluation

---

### 6.2 Citation Tasks & Implementation Choices

### Task 1: Source Attribution

**Goal:**  
Link each claim in the answer to its source chunk.

**Tasks:**
- Track which chunks contributed to the answer
- Format citations (inline, footnotes, or separate list)
- Provide enough context for user verification

**Implementation:**
- Include source markers in context during generation
- Instruct LLM to reference sources in output
- Post-process to extract and format citations

**Citation Format Options:**
- Inline: `According to the report [1], ...`
- Footnotes: `... the policy applies. [Source: policy.pdf, p.12]`
- Structured: JSON with `answer` and `sources` fields

---

### Task 2: Hallucination Control

**Goal:**  
Minimize answers that contradict or fabricate beyond the context.

**Tasks:**
- Constrain LLM via system prompt ("answer only from context")
- Detect when context is insufficient
- Provide "I don't know" responses when appropriate

**Implementation:**
- Prompt engineering (explicit constraints)
- Post-generation verification (optional, see Evaluation)
- Confidence thresholds on retrieval scores

**Important:**
- No technique eliminates hallucination entirely
- Multiple layers of defense are necessary
- Log suspected hallucinations for review

---

### Task 3: Confidence Indicators

**Goal:**  
Communicate answer reliability to users.

**Tasks:**
- Surface retrieval similarity scores
- Indicate number of supporting sources
- Flag low-confidence answers

**Implementation:**
- Expose scores in API response
- UI indicators (e.g., confidence badge)
- Threshold-based warnings

---

### 6.3 Citation Guarantees

At the end of citation processing:
- Every claim can be traced to a source
- Users can verify answers against originals
- Low-confidence answers are flagged

---

## 7. Evaluation

### 7.1 Purpose of Evaluation

Measure **system quality** across retrieval, generation, and grounding.

Evaluation provides:
- quantitative metrics
- regression detection
- improvement guidance

Evaluation does **not**:
- modify production data
- affect user-facing responses (unless gating)
- replace manual review

---

### 7.2 Evaluation Tasks & Implementation Choices

### Task 1: Retrieval Evaluation

**Goal:**  
Measure how well retrieval returns relevant chunks.

**Metrics:**
- **Recall@k**: Are the relevant chunks in the top-k?
- **Precision@k**: What fraction of top-k is relevant?
- **MRR**: Mean Reciprocal Rank of first relevant result

**Implementation:**
- Create a golden dataset: (query, relevant_chunk_ids) pairs
- Run queries against the system
- Compare retrieved chunks to ground truth

**Tools:**
- RAGAS: retrieval metrics
- Custom scripts with labeled data

---

### Task 2: Generation Evaluation

**Goal:**  
Measure answer quality.

**Metrics:**
- **Faithfulness**: Does the answer stick to the context?
- **Answer Relevance**: Does it address the question?
- **Fluency**: Is it well-written?

**Implementation:**
- LLM-as-Judge: Use an LLM to score answers
- Human evaluation for high-stakes use cases
- A/B testing for production

**Tools:**
- RAGAS: faithfulness, answer relevancy
- LangSmith: annotation and evaluation
- Custom Pydantic scoring functions

---

### Task 3: Grounding Evaluation

**Goal:**  
Measure how well answers are supported by sources.

**Metrics:**
- **Groundedness**: Is every claim backed by context?
- **Citation Accuracy**: Do citations point to supporting text?

**Implementation:**
- LLM-as-Judge with (answer, context, citations) input
- Automated fact-checking pipelines

---

### Task 4: Regression Testing

**Goal:**  
Detect when changes degrade system quality.

**Tasks:**
- Maintain a test suite of queries with expected behaviors
- Run tests on every significant change
- Alert on metric degradation

**Implementation:**
- Store test cases in version control
- CI/CD integration for automated testing
- Threshold-based pass/fail criteria

---

### 7.3 Evaluation Guarantees

At the end of evaluation:
- System quality is quantified
- Regressions are detectable
- Improvement priorities are data-driven

---

## 8. Serving / APIs

### 8.1 Purpose of Serving

Expose the RAG system to **users and applications** via well-defined interfaces.

Its output is:
- HTTP API endpoints
- Request/response contracts
- Access control

Serving does **not**:
- implement business logic (delegates to core modules)
- store persistent state
- perform background processing

---

### 8.2 Serving Tasks & Implementation Choices

### Task 1: API Framework

**Goal:**  
Provide a robust, typed, async API layer.

**Framework:**
- **FastAPI** (recommended)
- Alternative: FastMCP for MCP-compatible serving

**Why FastAPI:**
- Async-first (critical for LLM I/O)
- Automatic OpenAPI documentation
- Pydantic integration for validation
- Production-proven

---

### Task 2: Endpoint Design

**Goal:**  
Define clean, RESTful endpoints.

**Recommended Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/ingest` | POST | Trigger ingestion for a folder |
| `/query` | POST | Submit a question, get an answer |
| `/chunks` | GET | Inspect stored chunks (debug) |
| `/health` | GET | Health check |

**Request/Response:**
- Use Pydantic models for all request/response bodies
- Include clear error responses with codes

---

### Task 3: Authentication & Rate Limiting

**Goal:**  
Protect the API from abuse.

**Tasks:**
- API key authentication (start simple)
- Rate limiting per key
- Request logging for audit

**Implementation:**
- FastAPI dependencies for auth
- `slowapi` for rate limiting
- Middleware for request logging

**Important:**
- Start with API keys; OAuth later if needed
- Rate limit LLM-calling endpoints aggressively

---

### Task 4: Request Validation

**Goal:**  
Reject malformed requests early.

**Tasks:**
- Validate input types and ranges
- Sanitize user input
- Return helpful error messages

**Implementation:**
- Pydantic models with validators
- Custom exception handlers

---

### 8.3 Serving Guarantees

At the end of serving setup:
- All endpoints are documented (OpenAPI)
- Invalid requests fail fast with clear errors
- Access is controlled and logged

---

## 9. Observability & Cost Tracking

### 9.1 Purpose of Observability

Provide **visibility into system behavior**, **costs**, and **performance**.

Observability enables:
- debugging production issues
- tracking LLM costs
- identifying optimization opportunities

Observability does **not**:
- modify system behavior
- block requests
- replace testing

---

### 9.2 Observability Tasks & Implementation Choices

### Task 1: Structured Logging

**Goal:**  
Capture inspectable logs for every operation.

**Tasks:**
- Log all ingestion runs with file counts, durations
- Log all queries with latency, chunk counts
- Log all LLM calls with token usage

**Implementation:**
- Python `logging` with JSON formatter
- `structlog` for structured logging
- Correlation IDs for request tracing

**What to Log:**
- Timestamps
- Operation type
- Input/output sizes
- Latencies
- Errors with stack traces

---

### Task 2: LLMOps / Tracing

**Goal:**  
Deep visibility into LLM interactions.

**Tasks:**
- Trace every LLM call (prompt, response, tokens, latency)
- Aggregate traces into datasets
- Enable prompt debugging and iteration

**Tools:**
- **LangFuse** (open-source, self-hostable)
- **LangSmith** (LangChain ecosystem)
- **Opik** (Comet)
- **Pydantic Logfire**

**Recommended Start:**
- LangFuse (free tier, easy setup)
- Integrate via decorator or context manager

**Important:**
- Add tracing from day one
- Cost of not having visibility >> cost of tooling

---

### Task 3: Metrics Collection

**Goal:**  
Track quantitative system health.

**Tasks:**
- Request latency (p50, p95, p99)
- Token usage per request
- Error rates
- Queue depths (if async)

**Implementation:**
- Prometheus metrics
- FastAPI middleware for request metrics
- Custom counters for business metrics

---

### Task 4: Cost Tracking

**Goal:**  
Monitor and control LLM spend.

**Tasks:**
- Track tokens per model per request
- Calculate costs using pricing tables
- Alert on budget thresholds

**Implementation:**
- Log token counts from API responses
- Aggregate in observability tool or custom dashboard
- Set up alerts (daily spend, anomaly detection)

---

### 9.3 Observability Guarantees

At the end of observability setup:
- Every LLM call is traced
- Costs are tracked per request
- Debugging is possible without code changes
- Alerts exist for anomalies

---

## 10. Maintenance & Re-indexing

### 10.1 Purpose of Maintenance

Keep the RAG system **current, consistent, and performant** over time.

Maintenance handles:
- content updates
- embedding model migrations
- performance optimization

Maintenance does **not**:
- change core architecture
- add new features
- modify APIs

---

### 10.2 Maintenance Tasks & Implementation Choices

### Task 1: Incremental Updates

**Goal:**  
Add or update documents without full re-ingestion.

**Tasks:**
- Detect new or modified files (via hash comparison)
- Ingest only changed files
- Remove stale chunks when files are deleted

**Implementation:**
- File hash comparison against ingestion history
- Soft deletes with `deleted_at` timestamp
- Periodic cleanup of deleted chunks

---

### Task 2: Embedding Model Migration

**Goal:**  
Transition to a new embedding model safely.

**Tasks:**
- Re-embed all chunks with new model
- Store embeddings with model version
- Support parallel operation during migration

**Strategy:**
1. Add new embedding column or table
2. Backfill with new model
3. Switch retrieval to new embeddings
4. Deprecate old embeddings

**Critical:**
- Never mix embedding models in live retrieval
- Version everything
- Test retrieval quality before switching

---

### Task 3: Index Optimization

**Goal:**  
Maintain query performance as data grows.

**Tasks:**
- Monitor query latencies
- Rebuild or tune pgvector indexes
- Vacuum and analyze Postgres

**Implementation:**
- Schedule regular VACUUM ANALYZE
- Monitor index usage via pg_stat_user_indexes
- Consider IVFFlat or HNSW index tuning for scale

---

### Task 4: Data Cleanup

**Goal:**  
Remove outdated or irrelevant content.

**Tasks:**
- Identify and remove stale sources
- Archive old ingestion versions
- Maintain storage hygiene

**Implementation:**
- Retention policies (e.g., keep last 3 ingestion versions)
- Automated cleanup scripts
- Audit logs for deletions

---

### 10.3 Maintenance Guarantees

At the end of maintenance:
- All content is current
- Embeddings are versioned and consistent
- Performance is monitored
- Nothing is silently deleted

---

## 11. Error Handling & Resilience

### 11.1 Purpose

Handle failures gracefully across all phases.

---

### 11.2 Error Categories

| Phase | Error Type | Handling |
|-------|------------|----------|
| Ingestion | File parsing failure | Log, skip file, continue batch |
| Ingestion | Embedding API rate limit | Exponential backoff, retry |
| Retrieval | Database timeout | Retry with circuit breaker |
| Generation | LLM API error | Retry, fallback to cached response |
| Serving | Invalid request | Return 400 with details |

---

### 11.3 Resilience Patterns

**Retry with Backoff:**
- Use exponential backoff for transient failures
- Set max retries (e.g., 3–5)

**Circuit Breaker:**
- Stop calling failing services after threshold
- Fail fast, recover gradually

**Graceful Degradation:**
- Return partial results if some chunks fail
- Indicate degraded mode to user

**Implementation:**
- `tenacity` library for retries
- Custom circuit breaker or `pybreaker`
- Explicit error responses in API

---

## 12. Durable Workflows (Deferred)

### 12.1 Purpose

Add orchestration, retries, and caching at the workflow level.

---

### 12.2 When to Add

Add durable workflows when:
- Ingestion runs become long (>10 minutes)
- You need step-level caching for debugging
- You want to resume failed runs from last checkpoint

**Tools:**
- **DBOS** (Postgres-native, simple)
- **Prefect** (mature, more features)

**For Initial Learning:**
- Skip workflow orchestration
- Use simple scripts with error handling
- Add orchestration when pain is felt

---

## 5. Guiding Philosophy

> Build systems that are:
> - boring to operate  
> - easy to debug  
> - hard to misuse  

Correctness first. Automation later. Scale last.