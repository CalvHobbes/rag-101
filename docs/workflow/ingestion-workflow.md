# Ingestion Workflow

This document describes the DBOS-based workflow implementation for document ingestion.

---

## Overview

The ingestion workflow provides **durable, concurrent document processing** with:
- Resume-from-failure capability
- Parallel file processing (configurable concurrency)
- Step-level checkpointing
- Automatic retries for transient failures

---

## Architecture

```
ingest_folder_workflow(folder_path, run_id)     ← Umbrella workflow
    │
    ├─► discover_files_step()                   ← Returns FileInfo[]
    │
    └─► For each file via Queue (concurrency=3):
            │
            └─► process_file_workflow(file_info)  ← Child workflow
                    │
                    ├─► check_exists_step()
                    ├─► load_and_normalize_step()
                    ├─► chunk_step()
                    ├─► embed_step() [retries=3]
                    └─► save_step()
```

---

## Components

### Entry Point

```bash
# CLI usage
uv run python scripts/run_ingestion_workflow.py <folder_path>

# Or via Makefile
make ingest-workflow FOLDER=./data/documents
```

### Workflow Module

Located at: `src/ingestion/workflow.py`

| Component | Type | Description |
|-----------|------|-------------|
| `ingest_folder_workflow` | Workflow | Umbrella workflow for folder ingestion |
| `process_file_workflow` | Workflow | Per-file processing with checkpointing |
| `discover_files_step` | Step | File discovery (wraps existing function) |
| `load_and_normalize_step` | Step | Document loading and text normalization |
| `chunk_step` | Step | Document chunking |
| `embed_step` | Step | Embedding with retry (3 attempts) |
| `save_step` | Step | Database persistence |

---

## Configuration

### Environment Variables

```bash
# DBOS system database (uses same Postgres as RAG data)
DBOS_SYSTEM_DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# Optional: Connect to DBOS Conductor web console
DBOS_CONDUCTOR_KEY=  # Get from https://cloud.dbos.dev
```

### Concurrency

```python
# In src/ingestion/workflow.py
file_queue = Queue("file_processing_queue", worker_concurrency=3)
```

### Self-Hosted Conductor (Optional)

To monitor workflows via web UI, start Conductor:

```bash
docker-compose up -d dbos-conductor dbos-console
```

Then set in `.env`:
```bash
DBOS_CONDUCTOR_URL=ws://localhost:9090/
```

Access the console at: **http://localhost:9080**

---

## Advanced: Robust Resumption Strategy

The current implementation uses **Unique Run IDs** (simplified approach). This causes failed/incomplete workflows to be abandoned and restarted fresh on the next run. This is safe but can be inefficient if expensive steps (embedding) were partially completed.

To enable **cost-efficient resumption** without risking data corruption, use the following hybrid strategy:

### 1. Deterministic Child Workflow IDs
Use the file hash to generate the workflow ID for child workflows:
```python
# In ingest_folder_workflow
child_id = f"process-{file_dict['file_hash']}"
await file_queue.enqueue_async(..., workflow_id=child_id)
```
- **Unchanged Files:** DBOS returns cached result instantly (0 cost).
- **Failed Files:** DBOS retries the specific failure.
- **Changed Files:** New hash = New workflow (Runs fresh).

### 2. Safety Check (Required)
To prevent "zombie" workflows (manual retries of old IDs) from overwriting newer data, you MUST add a check in `save_step`:
```python
# In save_step
current_hash = get_file_hash(file_path)
if current_hash != processed_hash:
    logger.warning("File changed on disk! Aborting save.")
    return
```

### 3. Comparison
| Strategy | Pros | Cons |
|----------|------|------|
| **Unique IDs (Current)** | Simple, Safe | Re-runs expensive steps after crash |
| **file_hash IDs (Proposed)** | Saves $$ on resume | Requires strict safety checks |

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Concurrency** | `worker_concurrency=3` | Balance between parallelism and API rate limits |
| **Database** | Same Postgres | Minimize stack complexity |
| **Serialization** | FileInfo → dict at boundaries | DBOS requires serializable step I/O |
| **Error handling** | Continue on file failure | Other files still processed |

---

## Comparison with Manual Ingestion

| Aspect | `run_ingestion.py` | `run_ingestion_workflow.py` |
|--------|--------------------|-----------------------------|
| Resume capability | No (restart from scratch) | Yes (from last completed step) |
| Concurrency | Sequential | Parallel (queue-based) |
| Checkpointing | None | Per-step |
| Retry logic | Manual | Built-in via DBOS |
| Visibility | Logs only | DBOS events + logs |

---

## Related

- [Workflow Overview](overview.md)
- [Ingestion Overview](../ingestion/overview.md)
- [RAG Architecture - Durable Workflows](../RAG_ARCHITECTURE.md#310-durable-workflows-deferred)
