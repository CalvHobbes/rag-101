# Ingestion Overview

This document provides detailed implementation guidance for the RAG ingestion pipeline.

---

## 1. Purpose of Ingestion

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

## 2. Ingestion Tasks & Implementation Choices

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

## 3. Ingestion Guarantees

At the end of ingestion:

- Every vector maps to a known source
- Every chunk is traceable to a file and page
- Every embedding is reproducible
- Storage can be queried directly with SQL
