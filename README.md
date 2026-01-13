# RAG 101

A production-aligned modular RAG (Retrieval-Augmented Generation) system. This project demonstrates best practices in building a robust, observable, and resilient RAG pipeline.

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
├── generation/         # LLM interaction & RAG logic
├── ingestion/          # Document loading, chunking, embedding
├── retrieval/          # Semantic search & Query preprocessing
├── schemas/            # Pydantic models (Request/Response/Internal)
└── observability.py    # Tracing abstraction layer
tests/
├── unit/               # Isolated unit tests
└── integration/        # DB-connected tests
```
