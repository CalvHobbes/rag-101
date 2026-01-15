# Semantic Chunking vs Fixed-Size Chunking in RAG Systems

Chunking strategy has a **first-order impact on retrieval quality** in Retrieval-Augmented Generation (RAG) systems. This is especially true when using **small, fast embedding models** such as `all-MiniLM-L6-v2`.

This document explains **why semantic chunking consistently outperforms fixed-size chunking**, how it is implemented in production systems, and when fixed-size chunking is still acceptable.

---

## 1. Fixed-Size Chunking

### What It Is

Fixed-size chunking splits text purely based on length:
- Token count
- Character count
- With optional overlap

Typical configuration:
```text
Chunk size: 500 tokens
Overlap: 50 tokens
```

### Example

```text
[Chunk 1]
... end of paragraph about embeddings ...

[Chunk 2]
... middle of a new section about vector stores ...
```

### Why It’s Popular
- Easy to implement
- Deterministic
- Works acceptably for demos and tutorials

---

## 2. Semantic Chunking

### What It Is

Semantic chunking splits documents along **meaningful structural boundaries**, such as:
- Headings (H1–H4)
- Paragraphs
- Lists
- Sections
- Logical topic shifts

Small semantic units are **merged carefully** until a target size is reached.

> **Goal:** One chunk should represent **one coherent idea or topic**.

---

## 3. Why Semantic Chunking Works Better

### 3.1 Embeddings Compress Meaning Into One Vector

Embedding models represent an entire chunk using a **single vector**.

- Fixed-size chunking often mixes multiple topics
- The resulting embedding becomes a semantic “average”
- Similarity search becomes fuzzy and less reliable

Semantic chunking keeps embeddings **topic-pure**.

---

### 3.2 Fixed-Size Chunking Actively Hurts Recall

Consider this document structure:

```text
## Authentication
Explains OAuth, tokens, expiry.

## Rate Limits
Explains quotas, backoff, retries.
```

#### Fixed-Size Chunking Result

```text
Chunk:
"... OAuth tokens ... expiry ... Rate limits ... retries ..."
```

A query like:
> "How are rate limits handled?"

Produces a weak match because the embedding is diluted by authentication content.

#### Semantic Chunking Result

```text
Chunk:
"Rate limits, quotas, backoff, retries"
```

This chunk matches the query strongly and reliably.

---

### 3.3 Small Embedders Need Clean Signals

Models like MiniLM:
- Are fast and CPU-friendly
- Have limited semantic depth
- Depend heavily on clear topic boundaries

Semantic chunking compensates for model shallowness by providing **clean semantic input**.

---

## 4. Concrete Comparison

### Fixed-Size Chunk

Embedding roughly represents:
```text
{ OAuth, tokens, authentication, rate limits, retries }
```

### Semantic Chunk

Embedding represents:
```text
{ rate limits, quotas, backoff, retries }
```

Only the semantic chunk reliably answers:
> "What happens when I exceed API limits?"

---

## 5. How Semantic Chunking Is Implemented

Semantic chunking is **structured, not magical**.

### Step-by-Step Process

1. Parse document structure
   - Headings
   - Paragraphs
   - Lists

2. Treat each element as a **semantic unit**

3. Merge units until reaching a target size
   - Usually 300–500 tokens for MiniLM

4. Never merge across section boundaries

5. Attach metadata
   - Section title
   - Heading hierarchy
   - Document type

---

## 6. Simplified Pseudocode

```python
units = split_by_structure(document)

chunks = []
current = []

for unit in units:
    if token_count(current + unit) <= MAX_TOKENS:
        current.append(unit)
    else:
        chunks.append(current)
        current = [unit]

chunks.append(current)
```

**Critical rule:** Never combine semantic units from different sections.

---

## 7. Overlap: Semantic vs Fixed

### Fixed-Size Chunking
- Overlap is required
- Prevents cutting ideas in half
- Increases duplicate embeddings

### Semantic Chunking
- Ideas remain intact
- Overlap can be minimal or zero
- Smaller index size
- Less redundant data

---

## 8. Production Heuristics (MiniLM-Focused)

| Parameter | Recommendation |
|---|---|
| Target size | 300–500 tokens |
| Hard max | ~600 tokens |
| Overlap | 0–50 tokens |
| Split priority | Headings > paragraphs > lists |
| Metadata | Section title is essential |

---

## 9. When Fixed-Size Chunking Is Acceptable

Fixed-size chunking is still reasonable when:
- Documents are uniform and repetitive
- Text has little or no structure (logs, transcripts)
- Prototyping or quick experiments

For structured documents, semantic chunking consistently outperforms.

---

## 10. Key Takeaway

> **Embedding models do not forgive poor chunking.**

You can:
- Use a stronger embedding model, **or**
- Provide a weaker model with better chunks

In production systems, **semantic chunking is cheaper, safer, and more effective**.

---

## TL;DR

| Fixed-Size Chunking | Semantic Chunking |
|---|---|
| Splits by token count | Splits by meaning |
| Easy to implement | Slightly more complex |
| Mixes topics | Topic-pure |
| Lower recall | Higher recall |
| Requires overlap | Minimal overlap |

Semantic chunking is the default choice in mature RAG systems.
