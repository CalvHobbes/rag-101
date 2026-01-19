---
name: code-implementation-guardrail
description: Guide implementation of production-ready Python RAG components by enforcing correct abstractions, error handling, observability, and safety at coding time.
---

# Production Implementation Guardrail

## Goal
Ensure that **new or modified code** in a Python RAG system is implemented in a **production-ready way from the start**, not retrofitted later.

This skill is used **during active development**, not post-hoc review.

---

## When to Use This Skill
Use this skill when the user is:
- Implementing a new component
- Modifying core RAG logic
- Adding integrations (LLM, embeddings, DB, cache)
- Unsure how to implement something safely for production

---

## Instructions

1. Assume the user is actively writing or modifying code.
2. Identify the component being implemented (e.g., retriever, embedder, API handler).
3. Provide **implementation-level guidance**, not a backlog.
4. Enforce **production defaults**.
5. Be opinionated.

---

## Required Production Checks
For the component under implementation, explicitly address:

### 1. Interface & Responsibility
- What does this component own?
- What must it NOT do?
- What are its inputs and outputs?

### 2. Error Handling
- What failures are expected?
- Which are retriable?
- Which must fail fast?
- What is logged vs returned?

### 3. Configuration & Secrets
- What must be configurable?
- What must NOT be hardcoded?
- How are secrets injected?

### 4. Observability
- What must be logged?
- What metrics should be emitted?
- What trace spans should exist?

### 5. Performance & Cost
- What are the default limits?
- What guardrails exist (timeouts, batch sizes)?
- What prevents runaway cost?

### 6. Testing (Non-Optional)
- What unit tests are required?
- What integration tests must exist?
- What failure paths must be tested?

---

## Constraints
- ❌ Do not suggest “add later”
- ❌ Do not hand-wave production concerns
- ❌ Do not provide generic best practices
- ✅ Tie guidance directly to code being written
- ✅ Prefer explicit patterns over flexibility

---

## Output Format
Produce a **concise implementation checklist** and **code-level guidance** tailored to the specific component. When needed, update one or more of the  EXISTING documents :
1) docs/RAG_ARCHITECTURE.md
2) docs/IMPLEMENTATION_PLAN.md
3) docs/Progress_Tracker.md
Do NOT produce:
- Large backlogs
- Multi-category tables
- Architecture reviews

---

## Expected Outcome
The user can implement the code **once**, correctly, without needing a later hardening pass.