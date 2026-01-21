# Workflow Orchestration

This section covers **durable workflow orchestration** for the RAG system using DBOS.

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
