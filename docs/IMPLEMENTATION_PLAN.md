# Implementation Plan: RAG System

Build a production-aligned RAG system covering Ingestion and Retrieval phases.


---

## Table of Contents
- [Design Decisions](#design-decisions)
- [Best Practices](#best-practices-incorporated)
- [Phase 0: Setup](#phase-0-setup)
- [Phase 1: Ingestion Pipeline](#phase-1-ingestion-pipeline)
- [Phase 2: Retrieval](#phase-2-retrieval)
- [Phase 3: Generation](#phase-3-generation-rag)
- [Phase 4: Citations & Grounding](#phase-4-citations--grounding)
- [Phase 6: Serving / API](#phase-6-serving--api)
- [Phase 7: Observability](#phase-7-observability)
- [Phase 9: Error Handling & Resilience](#phase-9-error-handling--resilience)

---

## Design Decisions

> [!NOTE]
> **Embeddings**: Uses free local HuggingFace `all-MiniLM-L6-v2` (384 dimensions)

> [!NOTE]
> **Abstraction**: Embeddings and LLM are abstracted behind interfaces for easy swapping

> [!NOTE]
> **Architecture**: Layered design with schemas (Pydantic), models (SQLAlchemy), services, and factory pattern for DI

---

## Best Practices Incorporated

| Practice | What We're Adopting |
|----------|---------------------|
| **pydantic-settings** | Typed, validated config with nested settings classes |
| **Pydantic Schemas** | Separate schemas for Create vs Response patterns |
| **Custom Exceptions** | Hierarchical exception classes for clear error handling |
| **Factory Pattern** | `make_*()` functions for dependency injection |
| **SQLAlchemy Models** | UUID primary keys, proper timestamps |
| **Async Support** | Ready for async operations (optional for learning) |

---

## Phase 0: Setup

### - [x] Task 0.1: Project Structure

```
rag-101/
├── src/
│   ├── config.py              # pydantic-settings based config
│   ├── exceptions.py          # Custom exception hierarchy
│   ├── schemas/               # Pydantic validation schemas
│   │   ├── __init__.py
│   │   └── chunks.py          # ChunkCreate, ChunkResponse
│   ├── models/                # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── base.py
│   │   ├── source_document.py
│   │   └── chunk.py
│   ├── db/                    # Database setup
│   │   ├── __init__.py
│   │   └── db_manager.py
│   └── ingestion/             # Ingestion services
│       ├── __init__.py
│       ├── file_discovery.py
│       ├── document_loader.py
│       ├── text_normalizer.py
│       ├── chunker.py
│       ├── embedder.py
│       └── storage.py
├── scripts/
│   └── run_ingestion.py
├── tests/
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── pyproject.toml
```

---

### - [x] Task 0.2: Docker Compose for Postgres + pgvector

**File:** `docker-compose.yml`

| Component | Image | Purpose |
|-----------|-------|---------|
| Postgres | `pgvector/pgvector:pg16` | Database with vector extension |

**Ports:** `5432:5432`  
**Volumes:** Named volume `pgdata` (persists across restarts)

---

### - [x] Task 0.3: Config with pydantic-settings

**File:** `src/config.py`

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class EmbeddingSettings(BaseSettings):
    """Swappable embedding provider config."""
    provider: str = "huggingface"  # huggingface | openai | jina
    model: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    api_key: str = ""  # Required for openai/jina

class LLMSettings(BaseSettings):
    """Swappable LLM provider config (for Query phase)."""
    provider: str = "openai"  # openai | ollama | anthropic
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""  # For Ollama: http://localhost:11434

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore",
        env_nested_delimiter="__"  # Allows EMBEDDING__PROVIDER=openai
    )
    
    database_url: str = "postgresql://..."
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)

def get_settings() -> Settings:
    return Settings()
```

**Supported Embedding Providers:**

| Provider | Model Examples | Dimensions | Cost |
|----------|---------------|------------|------|
| `huggingface` | `all-MiniLM-L6-v2`, `bge-small-en` | 384 | Free |
| `openai` | `text-embedding-3-small` | 1536 | $0.02/1M tokens |
| `jina` | `jina-embeddings-v3` | 1024 | Free tier |

**Supported LLM Providers (for Query phase):**

| Provider | Model Examples | Notes |
|----------|---------------|-------|
| `openai` | `gpt-4o-mini`, `gpt-4o` | API key required |
| `ollama` | `llama3.2`, `mistral` | Local, free |
| `anthropic` | `claude-3-haiku` | API key required |

---

### - [x] Task 0.4: Custom Exceptions

**File:** `src/exceptions.py`

```python
# Base exceptions
class IngestionException(Exception): ...
class StorageException(Exception): ...

# Specific exceptions
class FileDiscoveryError(IngestionException): ...
class DocumentLoadError(IngestionException): ...
class ChunkingError(IngestionException): ...
class EmbeddingError(IngestionException): ...
class DatabaseConnectionError(StorageException): ...
```

---

### - [x] Task 0.5: Pydantic Schemas

**File:** `src/schemas/chunks.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class ChunkBase(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChunkCreate(ChunkBase):
    file_hash: str
    chunk_index: int
    embedding: list[float]

class ChunkResponse(ChunkBase):
    id: UUID
    chunk_id: str
    file_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

---

### - [x] Task 0.6: SQLAlchemy Models

**File:** `src/models/chunk.py`

```python
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
import uuid

class Chunk(Base):
    __tablename__ = "chunks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chunk_id = Column(Text, unique=True, nullable=False)
    file_id = Column(Integer, ForeignKey("ingestion_files.id"))
    content = Column(Text, nullable=False)
    embedding = Column(Vector(384))
    metadata = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### - [x] Task 0.7: Python Environment

**File:** `requirements.txt`

**Setup with `uv`:**
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

| Package | Purpose |
|---------|---------|
| `pydantic-settings` | Typed configuration |
| `sqlalchemy[asyncio]` | ORM with async support |
| `psycopg[binary]` | Postgres driver |
| `pgvector` | Vector extension |
| `langchain-community` | Document loaders |
| `langchain-huggingface` | HuggingFace embeddings |
| `sentence-transformers` | Local embedding models |
| `pypdf` | PDF parsing |
| `python-dotenv` | Environment variables |
| `tenacity` | Retry logic |

---

## Phase 1: Ingestion Pipeline

### - [x] Task 1.1: File Discovery

**File:** `src/ingestion/file_discovery.py`

| What | Details |
|------|---------|
| **Goal** | Traverse folder, find .txt/.pdf files, compute hashes |
| **Libraries** | `pathlib`, `hashlib` |
| **Returns** | List of `FileInfo` (Pydantic model) |
| **Raises** | `FileDiscoveryError` on failures |

---

### - [x] Task 1.2: Document Loading

**File:** `src/ingestion/document_loader.py`

| What | Details |
|------|---------|
| **Goal** | Load file content with metadata |
| **Framework** | LangChain |
| **Classes** | `PyPDFLoader`, `TextLoader` |
| **Raises** | `DocumentLoadError` on failures |

---

### - [x] Task 1.3: Text Normalization

**File:** `src/ingestion/text_normalizer.py`

| What | Details |
|------|---------|
| **Goal** | Clean text before chunking |
| **Libraries** | Plain Python (no dependencies) |
| **Operations** | Remove null chars, collapse newlines, strip whitespace |

---

### - [x] Task 1.4: Chunking

**File:** `src/ingestion/chunker.py`

| What | Details |
|------|---------|
| **Goal** | Split text into overlapping chunks |
| **Class** | `RecursiveCharacterTextSplitter` |
| **Parameters** | `chunk_size=800`, `chunk_overlap=100` |
| **Raises** | `ChunkingError` on failures |

**Chunk ID:** `sha256(file_hash:chunk_index)[:16]`

---

### - [x] Task 1.5: Embedding Generation

**File:** `src/ingestion/embedder.py`

| What | Details |
|------|---------|
| **Goal** | Convert chunks to vectors |
| **Factory** | `make_embedder()` returns configured embeddings |
| **Default** | `HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")` |
| **Raises** | `EmbeddingError` on failures |

---

### - [x] Task 1.6: Storage

**File:** `src/ingestion/storage.py`

| What | Details |
|------|---------|
| **Goal** | Persist to Postgres and handle updates |
| **Logic** | 1. Check if file path exists in DB <br> 2. If new hash != old hash, DELETE all old chunks for that file <br> 3. Insert new chunks |
| **Idempotency** | `ON CONFLICT DO NOTHING` on `chunk_id` (safe for re-runs of same content) |
| **Raises** | `StorageException` on failures |

---

### - [x] Task 1.7: Factory Functions
 
**File:** `src/ingestion/embedder.py` (Merged into embedder)

```python
from src.config import get_settings
from src.exceptions import EmbeddingError

def make_embedder():
    """Factory: returns configured embedding instance."""
    settings = get_settings().embedding
    
    match settings.provider:
        case "huggingface":
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(model_name=settings.model)
        case "openai":
            from langchain_openai import OpenAIEmbeddings
            return OpenAIEmbeddings(
                model=settings.model,
                api_key=settings.api_key
            )
        case "jina":
            from langchain_community.embeddings import JinaEmbeddings
            return JinaEmbeddings(
                model_name=settings.model,
                jina_api_key=settings.api_key
            )
        case _:
            raise EmbeddingError(f"Unknown provider: {settings.provider}")

def make_llm():
    """Factory: returns configured LLM instance (for Query phase)."""
    settings = get_settings().llm
    
    match settings.provider:
        case "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=settings.model, api_key=settings.api_key)
        case "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(model=settings.model, base_url=settings.base_url)
        case "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=settings.model, api_key=settings.api_key)
```

**To switch providers, just update `.env`:**
```bash
# Switch to OpenAI embeddings
EMBEDDING__PROVIDER=openai
EMBEDDING__MODEL=text-embedding-3-small
EMBEDDING__DIMENSION=1536
EMBEDDING__API_KEY=sk-...
```

---

### - [x] Task 1.8: Orchestration Script

**File:** `scripts/run_ingestion.py`

```bash
python scripts/run_ingestion.py --folder /path/to/docs
```

Pipeline: `discover → load → normalize → chunk → embed → store`

---

## Verification Plan

### Automated Tests

| Test | What it verifies |
|------|------------------|
| `test_normalizer` | Whitespace/null handling |
| `test_chunker` | Chunk sizes, overlap, deterministic IDs |
| `test_embedder` | Correct dimensions, swappable |
| `test_storage` | Idempotency, schema validation |

### Manual Verification

```bash
# 1. Start Postgres
docker compose up -d

# 2. Run ingestion
python scripts/run_ingestion.py --folder ./test_docs

# 3. Verify in DB
docker exec -it rag-postgres psql -U postgres -d rag -c \
  "SELECT chunk_id, LEFT(content, 50) FROM chunks LIMIT 5;"

# 4. Test idempotency - run again, expect 0 new rows
```

---

## Phase 2: Retrieval Pipeline

### - [x] Task 2.1: Query Preprocessing

**File:** `src/retrieval/query_preprocessor.py`

| What | Details |
|------|---------|
| **Goal** | Normalize user query before embedding |
| **Libraries** | Plain Python (reuses `normalize_text` from ingestion) |
| **Operations** | Strip whitespace, collapse all whitespace to single space |
| **Logging** | Original and processed query lengths |

---

### - [x] Task 2.2: Query Embedding

**File:** `src/retrieval/query_embedder.py`

| What | Details |
|------|---------|
| **Goal** | Convert query to vector using same model as ingestion |
| **Factory** | Reuses `get_embedder()` from `src/ingestion/embedder.py` |
| **Validation** | Checks embedding dimension matches config |
| **Raises** | `EmbeddingError` on failures |

**Critical:** Query embedding model **must match** document embedding model.

---

### - [x] Task 2.3: Similarity Search

**File:** `src/retrieval/similarity_search.py`

| What | Details |
|------|---------|
| **Goal** | Find top-k similar chunks using pgvector |
| **Operator** | `<=>` (cosine distance) via raw SQL |
| **Parameters** | `top_k` (default: 5), `distance_threshold` (optional) |
| **Returns** | List of dicts: `chunk_id`, `content`, `metadata`, `document_id`, `similarity` |
| **Raises** | `StorageException` on failures |

**file_path support:** Added JOIN with `source_documents` table to allow citations.
**Return Type:** Returns `RetrievalResult` objects (Pydantic models) instead of dicts.

**SQL Pattern:**
```sql
SELECT
    c.chunk_id,
    c.content,
    c.metadata,
    c.document_id,
    c.created_at,
    sd.file_path,
    1 - (c.embedding <=> :query_embedding) AS similarity
FROM chunks c
LEFT JOIN source_documents sd ON c.document_id = sd.id
WHERE (c.embedding <=> :query_embedding) < :threshold  -- (Optional)
ORDER BY c.embedding <=> :query_embedding
LIMIT :top_k
```

---

### - [x] Task 2.4: Retrieval Exceptions

**File:** `src/exceptions.py` (added to existing file)

```python
class RetrievalException(Exception): ...
class QueryPreprocessingError(RetrievalException): ...
class SimilaritySearchError(RetrievalException): ...
```

---

### - [x] Task 2.5: Retrieval Schemas

**File:** `src/schemas/retrieval.py`

**Design:** Uses inheritance from `ChunkResponse` for DRY code.

```python
from src.schemas.chunks import ChunkResponse

class RetrievalResult(ChunkResponse):
    similarity: float  # The only new field needed for retrieval

class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalResult]
    top_k: int
```

---

### - [x] Task 2.6: Metadata Filtering

**Goal:** Filter retrieval by source, date, or tags via SQL WHERE clauses.

**Tasks:**
- Add `filter` argument to `search_similar_chunks`
- Build dynamic SQL WHERE clause based on filter dict
- Expose filter in `retrieve` function

**Implementation:**
- **Schema:** `RetrievalFilter` Pydantic model with `source` and `file_type` fields
- **File Type Support:** `FileType` Enum (pdf, txt) mapped to SQL `ILIKE` patterns
- **Validation:** Uses `pydantic` to validate inputs
- **Logic:** Dynamic SQL generation appending `AND` clauses; `file_type` uses `c.metadata->>'source' ILIKE '%.ext'`
- **Flexibility:** `extra='allow'` for future extensibility

**Status:** ✅ Complete

---

### - [x] Task 2.7: Re-ranking

**Goal:** Improve retrieval precision by re-scoring top-k results with a cross-encoder.

**Implementation:**
- **Library:** `sentence-transformers`
- **Model:** `cross-encoder/ms-marco-MiniLM-L-6-v2` (Fast & accurate)
- **Logic:**
    1. Retrieve `top_k * 3` candidates (initial recall)
    2. Pass query + candidate pairs to CrossEncoder
    3. Sort by new score
    4. Return top `top_k`

**Status:** ✅ Complete

---

### - [x] Task 2.8: Retrieval Orchestration

**File:** `src/retrieval/retriever.py`

| What | Details |
|------|---------|
| **Goal** | Single entry point for the retrieval pipeline |
| **Function** | `retrieve(query, top_k)` |
| **Flow** | `preprocess` → `embed` → `similarity_search` → `RetrievalResponse` |
| **Exports** | Exposed via `src.retrieval` package |

**Usage:**
```python
from src.retrieval import retrieve
response = await retrieve("what is AI?", top_k=5)
```

---

## Retrieval Verification Plan

### Automated Tests

| Test | What it verifies |
|------|------------------|
| `test_query_preprocessor` | Whitespace handling, empty strings |

### Manual Verification

```bash
# 1. Ensure DB is running with ingested data
docker compose up -d

# 2. Test retrieval in Python REPL
python -c "
from src.retrieval import preprocess_query, embed_query, search_similar_chunks
import asyncio

query = preprocess_query('What is machine learning?')
embedding = embed_query(query)
results = asyncio.run(search_similar_chunks(embedding, top_k=3))
for r in results:
    print(f'{r[\"similarity\"]:.3f}: {r[\"content\"][:50]}...')
"
```

---

## Summary

| Phase | Tasks | Key Tech |
|-------|-------|----------|
| **Setup** | Structure, Docker, config, schemas, models, exceptions | pydantic-settings, SQLAlchemy |
| **Ingestion** | Discovery → Load → Normalize → Chunk → Embed → Store | LangChain, HuggingFace, factory pattern |
| **Retrieval** | Preprocess → Embed → Search → (Filter) → (Rerank) | pgvector, raw SQL, async |
| **Generation** | Retrieve → Format → Generate → Parse citations | LangChain, Gemini/OpenAI |
| **Citations** | Inline citations, source extraction | Regex parsing |
| **Serving** | `/query`, `/health` endpoints | FastAPI, Pydantic |
| **Observability** | Tracing, tagging, vendor-neutral abstraction | Opik, structlog |
| **Error Handling** | Retry logic, exception handlers, proper HTTP codes | tenacity, FastAPI |

## Phase 3: Generation (RAG)

### - [x] Task 3.1: Generation Schemas
**File:** `src/schemas/generation.py`
- `GenerateRequest`: query, filters, top_k
- `GenerateResponse`: answer, citation context

### - [x] Task 3.2: LLM Factory
**File:** `src/generation/llm_factory.py`
- Supports explicit provider switching (OpenAI, Gemini)
- Centralized configuration via `LLMProvider` Enum

### - [x] Task 3.3: Prompt Management
**File:** `src/generation/prompts.py`
- System prompt enforcing strict grounding ("If you don't know, say so")
- User prompt injecting context

### - [x] Task 3.4: Generation Service
**File:** `src/generation/service.py`
- Orchestrates: Retrieve -> Format -> Generate
- **Observability:** Integrated **Opik** for full tracing
- **Architecture:** Explicit control flow (no LCEL chains)

### - [x] Task 3.5: End-to-End Demo
**File:** `scripts/generate_demo.py`
- Verifies: Retrieval -> Reranking -> LLM Generation -> Opik Logging

---


## Phase 4: Citations & Grounding

### - [x] Task 4.1: Generation Schema Updates
**File:** `src/schemas/generation.py`

- **Field:** Add `citations: List[str]` to `GenerateResponse`.
- **Purpose:** Structured list of unique sources used in the answer for UI display.

### - [x] Task 4.2: System Prompt Updates
**File:** `src/generation/prompts.py`

- **Constraint:** Enforce strict inline citation format: `[Source: filename]`.
- **Instruction:** "Every claim must be immediately followed by a citation."

### - [x] Task 4.3: Service Logic
**File:** `src/generation/service.py`

- **Extraction Logic:** regex parse `[Source: (.*?)]` from answer.
- **Deduplication:** Unique list of sources.
- **Assignment:** Populate `response.citations`.

## Phase 6: Serving / API

### - [x] Task 6.1: FastAPI App Setup
**File:** `src/api/main.py`
- FastAPI app with lifespan events
- Async-first design with Pydantic validation
- Auto-generated OpenAPI docs at `/docs`

### - [x] Task 6.2: Query Endpoint
**File:** `src/api/routers/query.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/query` | Submit a question, get RAG answer |

**Request:** `GenerateRequest` (query, top_k, rerank, filter)
**Response:** `GenerateResponse` (answer, citations, retrieval_context)

### - [x] Task 6.3: Health Endpoint
**File:** `src/api/main.py`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Health check with dependency verification |

**Features:**
- Verifies database connectivity
- Returns 503 if dependencies are unhealthy
- Suitable for load balancer health checks

### - [x] Task 6.4: MCP Server
**File:** `src/mcp/server.py`

| Interface | Tool | Purpose |
|-----------|------|---------|
| MCP | `query_rag` | Exposes RAG query as tool for AI assistants |

**Features:**
- Provides same functionality as REST `/query` endpoint
- Equivalent error handling and observability
- Model warmup on startup (avoids first-call timeout)
- Logs to stderr (MCP uses stdout for JSON protocol)

---

## Phase 7: Observability

### - [x] Task 7.1: Observability Abstraction
**File:** `src/observability.py`
- **Goal:** Vendor-neutral tracing interface (Abstract Factory / Facade).
- **Components:**
    - `Phase` Enum (`ingestion`, `retrieval`, `generation`)
    - `@track(name, phase)` decorator
    - `configure_observability()`

### - [x] Task 7.2: Ingestion Tracing
**File:** `scripts/run_ingestion.py`
- Initialize using `src.observability`
- Trace ingestion run with `Phase.INGESTION`

### - [x] Task 7.3: Component Refactoring
**Files:** `src/generation/service.py`, `src/retrieval/retriever.py`
- Replace direct `@opik.track` with `@observability.track`

### - [ ] Task 7.4: Request ID Correlation
- **Goal:** Correlate API requests with Opik traces.
- **Implementation:**
    - Generate `request_id` in API middleware or entry point.
    - Pass `request_id` to `track()` decorator or Opik context.
    - Ensure `request_id` is logged in both application logs and Opik metadata.

---

## Phase 9: Error Handling & Resilience

### - [x] Task 9.1: LLM Exception Classes
**File:** `src/exceptions.py`
- `LLMError` - Base exception for LLM errors
- `LLMRateLimitError` - Rate limit exceeded (429)
- `LLMTimeoutError` - Request timeout

### - [x] Task 9.2: Retry Logic
**File:** `src/generation/service.py`
- Uses `tenacity` for automatic retries
- **Smart Backoff**: Parses `retry after` from 429 errors.
- **Fail-Fast**: Aborts immediately if wait > 5s (prevents hanging).
- Fallback: Exponential backoff (2s -> 10s max) for other transient errors.
- 6 attempts max.

### - [x] Task 9.3: API Exception Handlers
**File:** `src/api/exception_handlers.py`

| Exception | HTTP Status | Response |
|-----------|-------------|----------|
| `LLMRateLimitError` | 429 | Rate limit exceeded |
| `LLMTimeoutError` | 503 | LLM request timed out |
| `LLMError` | 503 | LLM service unavailable |
| `SimilaritySearchError` | 503 | Search service unavailable |
| `StorageException` | 503 | Database service unavailable |
| `QueryPreprocessingError` | 400 | Invalid query format |

### - [x] Task 9.4: Graceful Degradation
- Return partial results when LLM fails
- **Fallback**: Returns retrieved documents and citations if Generation fails (e.g. Rate Limit).

### - [x] Task 9.5: Timeouts
- Explicit timeout configuration for LLM, embedding, and DB calls

