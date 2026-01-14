# Generation Overview

This document provides detailed implementation guidance for the RAG generation pipeline, including citation and grounding strategies.

---

## 1. Purpose of Generation

Generation converts **retrieved context + user query** into a **natural language answer**.

Its output is:
- synthesized answer text
- (optionally) structured response with citations

Generation does **not**:
- retrieve documents
- persist state
- evaluate answer quality

---

## 2. Generation Tasks & Implementation Choices

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

## 3. Generation Guarantees

At the end of generation:
- Answer is derived only from provided context
- Token usage is tracked
- Full prompt and response are logged
- No external data sources were accessed

---

## 4. Citation & Grounding

### 4.1 Purpose of Citation & Grounding

Ensure answers are **traceable to sources** and **factually grounded** in retrieved content.

Its output is:
- answer with inline or footnote citations
- grounding confidence indicators

Citation does **not**:
- generate new content
- modify source data
- replace evaluation

---

### 4.2 Citation Tasks & Implementation Choices

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

### 4.3 Citation Guarantees

At the end of citation processing:
- Every claim can be traced to a source
- Users can verify answers against originals
- Low-confidence answers are flagged

> **📖 For detailed citation verification strategies** (including latency optimization, selective verification, and production approaches), see **[Citation Verification Strategies](citation-verification.md)**
