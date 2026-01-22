# Workflow Orchestration

This section covers **durable workflow orchestration** for the RAG system using DBOS.

## Table of Contents

- [Overview](#overview)
- [When to Use Workflows](#when-to-use-workflows)
- [Architecture](#architecture)
- [Key Concepts](#key-concepts)
- [Implementation](#implementation)
- [References](#references)
- [Technical Findings](#technical-findings)

---

## Overview

### What is Workflow Orchestration?

Workflow orchestration provides **durable execution** - the ability to resume long-running operations from the last completed step after failures, crashes, or restarts.

### Why DBOS?

| Consideration | DBOS Advantage |
|---------------|----------------|
| **Postgres-native** | Uses same database as RAG data - no new infrastructure |
| **Lightweight** | Simple library, not a separate orchestration server |
| **Python-first** | Decorators on existing functions, minimal code changes |
| **Resume-from-failure** | Checkpoints each step, resumes from last success |

---

## When to Use Workflows

Per [RAG_ARCHITECTURE.md](../RAG_ARCHITECTURE.md#310-durable-workflows-deferred), workflows are appropriate when:

- Ingestion runs exceed 10 minutes
- Need step-level caching for debugging
- Want to resume failed runs from checkpoint

---

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                     DBOS Workflow System                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Workflow (umbrella)                                                   │
│      │                                                                  │
│      ├─► Step 1: Discover files                                        │
│      │                                                                  │
│      └─► Queue (concurrent execution):                                 │
│              │                                                          │
│              └─► Child Workflow (per file)                             │
│                      │                                                  │
│                      ├─► Step: Load & normalize                        │
│                      ├─► Step: Chunk                                   │
│                      ├─► Step: Embed (with retries)                    │
│                      └─► Step: Save                                    │
│                                                                         │
│  ┌──────────────────┐                                                  │
│  │  Postgres        │ ← Checkpoints, queue state, recovery data       │
│  │  (same as RAG DB)│                                                  │
│  └──────────────────┘                                                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts

### Workflows
- Annotated with `@DBOS.workflow()`
- Must be **deterministic** - same inputs produce same step calls
- Orchestrate multiple steps

### Steps
- Annotated with `@DBOS.step()`
- **Checkpointed** - output saved to database
- Can have **retries** for transient failures
- Must be **idempotent**

### Queues
- Enable **concurrent execution** with flow control
- `worker_concurrency` limits parallel executions
- First-in, first-out (FIFO) ordering

### Retry & Resume Behavior

DBOS distinguishes between **step-level retries** and **workflow-level resume**:

**Step-Level Retries:**
```python
@DBOS.step(retries_allowed=True, max_attempts=3, backoff_rate=2.0)
```
- Configured per-step via decorator
- Automatic retry on transient failures (e.g., API rate limits)

**Workflow-Level Resume:**

| Workflow Status | Resume Available? | Method |
|-----------------|-------------------|--------|
| `CANCELLED` | ✅ Yes | `DBOS.resume_workflow(workflow_id)` |
| `MAX_RECOVERY_ATTEMPTS` | ✅ Yes | `DBOS.resume_workflow(workflow_id)` |
| `ERROR` | ❌ No | Use `fork_workflow()` to restart from specific step |

> [!NOTE]
> In DBOS Conductor, the **Resume** button is only enabled for `CANCELLED` or `MAX_RECOVERY_ATTEMPTS` workflows.
> Workflows with `ERROR` status are considered "completed with failure" - use `fork_workflow()` to retry from a specific step.

---

## Implementation

See [ingestion-workflow.md](ingestion-workflow.md) for the specific implementation of workflow-based document ingestion.

---

## References

- [DBOS Programming Guide](https://docs.dbos.dev/python/programming-guide)
- [DBOS Architecture](https://docs.dbos.dev/architecture)
- [DBOS Queues](https://docs.dbos.dev/python/tutorials/queue-tutorial)

---

## Technical Findings

Key learnings and constraints discovered during implementation:

### 1. Method Signatures & Context
- **Context Handling**: Every workflow, step, and transaction must accept the context object as its first argument.
    - `workflow(ctx: WorkflowContext, ...)`
    - `step(ctx: StepContext, ...)`
- **Decorators**: The decorators `@DBOS.workflow()` and `@DBOS.step()` are required to register functions with the DBOS runtime. If the ingestion flow has been broken down into clear steps, then it's just a matter of adding these decorators to the existing functions.

### 2. Serialization Requirements
- **JSON Compatibility**: All input arguments and return values for steps and workflows must be JSON-serializable.
- **Pydantic Models**: Complex objects should be converted to Pydantic models (or dictionaries) at the workflow boundary. Passing raw arbitrary Python objects (like open file handles or complex class instances) will fail.

### 3. Error Handling & Resumption
- **Cancellation Propagation**: If a child workflow is cancelled, that cancellation bubbles up to the parent workflow as an error.
- **Resumption Limitations**: The `DBOS.resume_workflow` capability is strictly limited.
    - **Can Resume**: Workflows in `CANCELLED` or `TIMEOUT` status.
    - **Cannot Resume**: Workflows in `ERROR` status (i.e., threw an exception). These must be handled by retrying (via `fork_workflow`) or fixing the underlying issue and restarting.

### 4. Observability Integration (Opik)
- **Tracing Isolation**: Combining DBOS's internal OTel traces with an external tracing system (like Opik) is complex due to trace ID conflicts ("Split Brain" issue where DBOS generates different internal and external trace IDs). See [Hybrid Tracing Analysis](../observability/hybrid_tracing.md) for details.
- **Best Practice**: 
    - Use **Opik SDK** (`@track`) separately for application-level tracing, including the workflow execution.
    - Do not attempt to merge the two trace trees.
