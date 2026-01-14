# Retrieval Overview

This document provides detailed implementation guidance for the RAG retrieval pipeline.

---

## 1. Purpose of Retrieval

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

## 2. Retrieval Tasks & Implementation Choices

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

## 3. Retrieval Guarantees

At the end of retrieval:
- Every returned chunk is traceable to its source
- Similarity scores are interpretable
- Query and results are logged for debugging
- No answer generation has occurred
