# RAG 101

A production-aligned modular RAG (Retrieval-Augmented Generation) system built as a learning journey. This project explores patterns and practices I've gleaned while learning to build robust, observable, and resilient RAG pipelines—practices that continue to evolve as my understanding deepens.

## 🚀 Key Features

- **Ingestion Pipeline**: Robust document processing with normalization, chunking, and embedding.
- **Advanced Retrieval**: Semantic search using vector similarity (pgvector).
- **Resilience**: 
  - Retry logic with exponential backoff for LLM calls.
  - Graceful degradation (fallback to search results if LLM fails).
  - Explicit timeouts for DB, Parsing, and External APIs.
- **Observability**: Vendor-neutral tracing abstraction (currently unified with Opik).
- **Modern Stack**: Python 3.11, FastAPI, SQLAlchemy (Async), Pydantic V2, `uv` for package management.

## 🛠️ Quick Start

### 1. Prerequisites
- Docker (for PostgreSQL + pgvector)
- `uv` (modern Python package manager)

### 2. Environment Setup
Copy the example environment file and fill in your API keys:
```bash
cp .env.example .env
```
Required keys: `OPENAI_API_KEY` (or equivalent), `DATABASE_URL`.

### 3. Start Database
```bash
docker compose up -d
```

### 4. Install Dependencies
```bash
uv sync
```

### 5. Run Ingestion
Ingest documents from a folder:
```bash
uv run scripts/run_ingestion.py --folder /path/to/docs
```

### 6. Start the API Server
```bash
uv run uvicorn src.api.main:app --reload
```

## 🔌 API Endpoints

The API is built with FastAPI. Once running, you can access the automatic interactive documentation at `http://localhost:8000/docs`.

### Primary Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **POST** | `/query` | **Main RAG Endpoint**. Submits a user query and returns a generated answer with citations. |
| **GET** | `/health` | **Health Check**. Verifies DB connectivity. Returns 503 if DB is unreachable. |

#### Example `/query` Request
```json
{
  "query": "What are the safety protocols?",
  "top_k": 3
}
```

#### Example `/query` Response
```json
{
  "query": "What are the safety protocols?",
  "answer": "The safety protocols include... [Source: manual.pdf]",
  "citations": ["manual.pdf"],
  "retrieval_context": { ... }
}
```

## 🧪 Testing

The codebase maintains a strict separation between fast unit tests and slower integration tests.

### Run All Tests
```bash
uv run pytest
```

### Run Unit Tests (Fast, No DB)
```bash
uv run pytest tests/unit
```

### Run Integration Tests (Slow, Requires DB)
```bash
uv run pytest tests/integration
```
*Note: Ensure your Docker database is running before executing integration tests.*

## 📂 Project Structure

```bash
src/
├── api/                # FastAPI application & routers
├── config.py           # Configuration & Settings (Pydantic)
├── db/                 # Database connection & session management
├── exceptions.py       # Custom exception hierarchy
├── generation/         # LLM interaction & RAG logic
├── ingestion/          # Document loading, chunking, embedding
├── logging_config.py   # Structured logging configuration
├── models/             # SQLAlchemy ORM models
├── observability.py    # Tracing abstraction layer
├── retrieval/          # Semantic search & query preprocessing
└── schemas/            # Pydantic models (Request/Response/Internal)

tests/
├── unit/               # Isolated unit tests
└── integration/        # DB-connected tests

scripts/                # Operational scripts
├── run_ingestion.py    # Document ingestion pipeline
└── generate_demo.py    # End-to-end RAG demo

docs/                   # Architecture & design documentation
```

## 🗺️ Development Roadmap

This project is being built in phases as I learn and explore production-ready RAG development patterns.

### 📦 Phase 1: Foundation (Complete) ✅

Core RAG pipeline with observability foundation.

| Area | Features | Status |
|------|----------|:------:|
| **Ingestion** | File discovery, document loading, text normalization, chunking, embedding generation, hash-based idempotency | ✅ |
| **Retrieval** | Query preprocessing, vector similarity search, metadata filtering, reranking | ✅ |
| **Generation** | LLM factory (swappable providers), prompt management, citation extraction, retry logic with exponential backoff | ✅ |
| **API** | FastAPI setup, `/query` endpoint, `/health` with DB checks, exception handlers | ✅ |
| **Observability** | Vendor-neutral tracing abstraction (Opik), structured logging, phase-based tagging, graceful degradation | ✅ |
| **Resilience** | Custom exception hierarchy, timeouts (DB/LLM/parsing), graceful degradation, retry logic | ✅ |
| **Data** | PostgreSQL + pgvector, SQLAlchemy async, idempotency checks, hash-based change detection | ✅ |

### 🔧 Phase 2: Advanced Features (Planned)

Next areas to explore as I continue learning:

| Phase | Area | Planned Features | Status |
|-------|------|------------------|:------:|
| **Phase 4** | **Citation & Grounding** | Citation verification (heuristics, LLM-as-judge), groundedness checks, verification cache | ⬜ |
| **Phase 5** | **Evaluation & Testing** | RAGAS evaluation (faithfulness, relevance), Recall@k/MRR metrics, golden dataset, integration tests, regression test suite | ⬜ |
| **Phase 6** | **API Security** | API key authentication, rate limiting, request correlation IDs | ⬜ |
| **Phase 7** | **Advanced Observability** | Prometheus metrics endpoint, cost tracking dashboard, alerting on SLO violations | ⬜ |
| **Phase 8** | **Maintenance & Scaling** | HNSW index tuning for pgvector, embedding model migration, data retention policies | ⬜ |
| **Phase 9** | **Enhanced Resilience** | Circuit breaker pattern for LLM calls, batch error handling improvements | ⬜ |
| **Phase 10** | **Workflow Orchestration** | Evaluate need for durable workflows, step-level caching, checkpoint/resume capabilities | ⬜ |

**Current Learning Focus**: Building out evaluation infrastructure (Phase 5) to measure quality before adding advanced features.

## 📚 Documentation

Comprehensive guides for each system component:

- **[RAG Architecture](https://github.com/CalvHobbes/rag-101/blob/main/docs/RAG_ARCHITECTURE.md)** - Core principles, system design, and phased architecture
- **[Patterns & Principles](https://github.com/CalvHobbes/rag-101/blob/main/docs/PATTERNS_AND_PRINCIPLES.md)** - Design philosophy and best practices
- **[Ingestion Overview](https://github.com/CalvHobbes/rag-101/blob/main/docs/ingestion/overview.md)** - Document processing pipeline
- **[Retrieval Overview](https://github.com/CalvHobbes/rag-101/blob/main/docs/retrieval/overview.md)** - Semantic search and reranking
- **[Generation Overview](https://github.com/CalvHobbes/rag-101/blob/main/docs/generation/overview.md)** - LLM integration and prompting
- **[Observability Overview](https://github.com/CalvHobbes/rag-101/blob/main/docs/observability/overview.md)** - Tracing, logging, and monitoring

---

**Built with ❤️ as a learning project for production-grade RAG systems**
