# RAG Architecture

This document defines the **architecture, principles, and phased design**
for a **production-grade Retrieval-Augmented Generation (RAG) system**.

It is intended to be a **living system blueprint**, not a tutorial or a demo.
The focus is on **correctness, inspectability, and long-term maintainability**.
The guiding force and principles behind this architecture is https://www.decodingai.com/p/my-ai-production-tech-stack/.

---

## Table of Contents
- [1. Core Principles](#1-core-principles)
- [2. System Architecture](#2-system-architecture)
- [3. RAG System Phases](#3-rag-system-phases)
- [4. Guiding Philosophy](#4-guiding-philosophy)

### Detailed Phase Documentation
- **[Ingestion Overview](ingestion/overview.md)** - Document processing and storage
- **[Retrieval Overview](retrieval/overview.md)** - Query processing and search
- **[Generation Overview](generation/overview.md)** - Answer generation and citations
  - [Citation Verification Strategies](generation/citation-verification.md)
- **[Observability Overview](observability/overview.md)** - Monitoring and tracing
- **[Testing & Evaluation Overview](testing/overview.md)** - Quality assurance

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

If you can't inspect a step, you can't trust it.

---

### 1.6 Delay Automation & Orchestration
- No file watchers
- No schedulers
- No workflow engines
- Deterministic ingestion runs first; automation later

---

## 2. System Architecture

![RAG System Architecture](rag%20101%20architecture%20image.png)

### Flow Summary

| Phase | Input | Output | Key Components |
|-------|-------|--------|----------------|
| **Ingestion** | Raw documents | Stored vectors + metadata | Loader → Normalizer → Chunker → Embedder |
| **Retrieval** | User query | Ranked chunks | Query embed → Similarity search → Re-rank |
| **Generation** | Query + Context | LLM response | Prompt assembly → LLM call → Parse |
| **Citation** | Response + Sources | Grounded answer | Attribution → Hallucination check |

---

## 3. RAG System Phases

### 3.1 Ingestion

**Purpose:** Convert raw documents into durable, retrievable knowledge units.

**Key Tasks:**
- File discovery & state tracking (hash-based)
- Document loading (PyMuPDF for PDFs)
- Text normalization
- Chunking with overlap (700-900 chars)
- Embedding generation (versioned models)
- Vector + metadata storage (Postgres + pgvector)
- Idempotency & re-run safety

**Storage Guarantees:**
- Every vector maps to a known source
- Every chunk is traceable to file and page
- SQL-queryable for debugging

📖 **[Detailed Ingestion Guide →](ingestion/overview.md)**

---

### 3.2 Retrieval

**Purpose:** Convert user query into ranked set of relevant chunks.

**Key Tasks:**
- Query preprocessing & normalization
- Query embedding (must match ingestion model)
- Similarity search (pgvector with cosine distance)
- Metadata filtering (pre or post-search)
- Optional re-ranking (cross-encoder)

**Retrieval Guarantees:**
- Every chunk is traceable to source
- Similarity scores are logged
- No answer generation performed

📖 **[Detailed Retrieval Guide →](retrieval/overview.md)**

---

### 3.3 Generation

**Purpose:** Convert retrieved context + query into natural language answer.

**Key Tasks:**
- Context assembly with source markers
- Prompt template design (versioned)
- LLM invocation with retry logic
- Response parsing & validation

**Generation Guarantees:**
- Answer derived only from provided context
- Token usage tracked for cost monitoring
- Full prompt/response logged

📖 **[Detailed Generation Guide →](generation/overview.md)**

---

### 3.4 Citation & Grounding

**Purpose:** Ensure answers are traceable and factually grounded.

**Key Tasks:**
- Source attribution (inline or structured)
- Hallucination control via prompt constraints
- Confidence indicators for reliability

**Citation Guarantees:**
- Every claim traceable to source
- Users can verify against originals
- Low-confidence answers flagged

📖 **Detailed Guides:**
- [Generation Overview](generation/overview.md#4-citation--grounding)
- [Citation Verification Strategies](generation/citation-verification.md)

---

### 3.5 Evaluation & Testing

**Purpose:** Measure system quality and prevent regressions.

**Key Metrics:**
- **Retrieval:** Recall@k, Precision@k, MRR
- **Generation:** Faithfulness, Answer Relevance
- **Grounding:** Groundedness, Citation Accuracy
- **Regression:** Test suite with thresholds

**Evaluation Tools:**
- RAGAS for RAG-specific metrics
- LLM-as-Judge for quality scoring
- Golden datasets for regression testing

📖 **[Detailed Testing & Evaluation Guide →](testing/overview.md)**

---

### 3.6 Serving / APIs

**Purpose:** Expose RAG system via production-ready interfaces.

**Recommended Stack:**
- **Framework:** FastAPI (async-first, typed)
- **Endpoints:** `/query` (POST), `/health` (GET)
- **Validation:** Pydantic models
- **Auth:** API key authentication
- **Rate Limiting:** Per-key quotas

**API Guarantees:**
- OpenAPI documentation auto-generated
- Invalid requests fail fast with clear errors
- Access controlled and logged

**Implementation:**
```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    question: str
    top_k: int = 5

@app.post("/query")
async def query(request: QueryRequest):
    # Orchestrate: Retrieve → Generate → Cite
    pass

@app.get("/health")
async def health():
    # Verify database, embeddings, LLM connectivity
    pass
```

---

### 3.7 Observability

**Purpose:** Provide visibility into system behavior, costs, and performance.

**Key Components:**
- **Abstraction Layer:** Vendor-neutral facade (Opik, LangFuse, LangSmith)
- **Structured Logging:** JSON logs with correlation IDs
- **LLM Tracing:** Track prompts, responses, tokens, latency
- **Metrics:** Request latency, token usage, error rates
- **Cost Tracking:** Per-request LLM spend monitoring

**Observability Guarantees:**
- Every LLM call traced
- Costs tracked per request
- Debugging possible without code changes

📖 **[Detailed Observability Guide →](observability/overview.md)**

---

### 3.8 Maintenance & Re-indexing

**Purpose:** Keep RAG system current and performant over time.

**Key Tasks:**
- **Incremental Updates:** Hash-based change detection
- **Embedding Model Migration:** Parallel operation during transition
- **Index Optimization:** Regular VACUUM ANALYZE, HNSW tuning
- **Data Cleanup:** Retention policies, audit logs

**Maintenance Strategy:**
1. Add new embedding column/table
2. Backfill with new model
3. Switch retrieval to new embeddings
4. Deprecate old embeddings

**Critical:** Never mix embedding models in live retrieval without versioning.

---

### 3.9 Error Handling & Resilience

**Purpose:** Handle failures gracefully across all phases.

**Error Categories:**

| Phase | Error Type | Handling |
|-------|------------|----------|
| Ingestion | File parsing failure | Log, skip file, continue batch |
| Ingestion | Embedding API rate limit | Exponential backoff, retry |
| Retrieval | Database timeout | Retry with circuit breaker |
| Generation | LLM API error | Retry, fallback to cached response |
| Serving | Invalid request | Return 400 with details |

**Resilience Patterns:**
- **Retry with Backoff:** Exponential backoff for transient failures
- **Circuit Breaker:** Stop calling failing services after threshold
- **Graceful Degradation:** Return partial results if some chunks fail

**Implementation:**
- `tenacity` library for retries
- Custom circuit breaker or `pybreaker`
- Explicit error responses in API

---

### 3.10 Durable Workflows (Deferred)

**When to Add:**
- Ingestion runs exceed 10 minutes
- Need step-level caching for debugging
- Want to resume failed runs from checkpoint

**Tools:**
- **DBOS** (Postgres-native, simple)
- **Prefect** (mature, more features)

**For Initial Learning:**
- Skip workflow orchestration
- Use simple scripts with error handling
- Add orchestration when pain is felt

---

## 4. Guiding Philosophy

> Build systems that are:
> - boring to operate  
> - easy to debug  
> - hard to misuse  

Correctness first. Automation later. Scale last.

---

## Deferred but Acknowledged Design Areas

The following areas are **intentionally deferred**.
They are understood, explicitly bounded, and constrained to prevent
accidental architectural drift or premature complexity.

Deferral does **not** imply ignorance.
It is a deliberate choice based on current scale, requirements, and
operational maturity.

---

### Deferred: RAG Orchestration Contract

**Why this matters**

In production systems, implicit orchestration logic tends to leak across
API handlers, prompts, and framework glue code, making the system harder
to debug, test, and evolve.

A clearly defined orchestration boundary enables:
- deterministic execution flow
- consistent observability
- simpler evaluation and testing

**Why this is deferred**

The current system follows a simple, linear flow
(Retrieve → Generate → Cite).
Introducing a formal orchestration layer at this stage would add
abstraction overhead without proportional benefit.

**Constraints (Must Hold Even While Deferred)**

- Orchestration logic must remain centralized in a single module
- API handlers must not embed retrieval or generation logic
- No RAG phase may call another phase directly outside the orchestration path

This section will be formalized when:
- multi-step workflows are required, or
- phase-specific retries or fallbacks are introduced, or
- partial result handling becomes necessary

---

### Deferred: State & Session Semantics

**Why this matters**

Multi-turn interactions introduce ambiguity around grounding,
retrieval scope, and answer provenance.
Without explicit rules, conversational memory can silently undermine
correctness guarantees.

**Why this is deferred**

This system is intentionally designed as a **single-turn, stateless RAG**
pipeline.
Conversational support would require explicit decisions around:
- memory representation
- retrieval-time context injection
- summarization and truncation guarantees

These are not currently required.

**Constraints (Must Hold Even While Deferred)**

- Each request must be processed independently
- No prompt accumulation across requests
- No implicit or hidden conversational memory

Any future conversational support must be implemented as an explicit
retrieval-time mechanism, not prompt carryover.

---

### Deferred: Security & Abuse Considerations

**Why this matters**

RAG systems are vulnerable to:
- prompt injection
- retrieval poisoning
- unintended data leakage through model responses

A formal threat model is required for regulated or multi-tenant
deployments.

**Why this is deferred**

The current deployment assumes a controlled environment with trusted
inputs and limited exposure.
A full security and abuse model would introduce operational and process
overhead that is not yet required.

**Constraints (Must Hold Even While Deferred)**

- Retrieved content must always be treated as untrusted input
- Prompts must explicitly constrain the model to provided context
- User-supplied content must not directly modify system prompts
- Retrieved documents must never be executed or interpreted as code

A formal threat model will be added prior to any external-facing or
multi-tenant deployment.

---

### Deferred: Configuration & Version Control Plane

**Why this matters**

Production RAG systems require coordinated versioning across:
- prompts
- embedding models
- chunking strategies
- retrieval logic

Without a control plane, rollbacks and audits become difficult.

**Why this is deferred**

At the current stage:
- version changes are infrequent
- versions are defined in code
- rollback is handled via code reversion

This keeps the system simpler while stabilizing core behavior.

**Constraints (Must Hold Even While Deferred)**

- Version identifiers must be explicit in code and logs
- Multiple embedding versions must never mix within a single retrieval path
- Any version change must be observable through tracing or metadata

A dedicated configuration plane will be introduced when:
- concurrent experiments are required, or
- live A/B testing is introduced, or
- frequent prompt or model iteration becomes necessary

---

### Explicit Non-Goals (For Now)

The following capabilities are intentionally out of scope:

- Autonomous or self-directed agents
- Tool execution or action-taking by the LLM
- Self-modifying prompts or online learning
- Implicit conversational memory
- Background workflow orchestration

These are excluded to preserve:
- determinism
- inspectability
- correctness guarantees

Any future expansion must not weaken these properties.
