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

**CLI (Manual/Batch):**
```bash
# CLI usage
uv run python scripts/run_ingestion_workflow.py <folder_path>

# Or via Makefile
make ingest-workflow FOLDER=./data/documents
```

**REST API (Programmatic):**
```bash
# Start ingestion (returns immediately with workflow ID)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"folder_path": "./data/documents"}'

# Response: {"workflow_id": "ingestion-abc123", "status": "started", ...}

# Poll status
curl http://localhost:8000/ingest/ingestion-abc123/status
```

> [!NOTE]
> The REST API returns immediately with a workflow ID. Use the status endpoint to poll for completion.
> DBOS is initialized in FastAPI's lifespan, so workflows persist across requests and survive server restarts.

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

## Resumption Strategy

The workflow implements a **Robust Resumption Strategy** to ensure cost-efficiency and data integrity.

### 1. Deterministic Child Workflow IDs
Child workflows (`process_file_workflow`) use the **file hash** as their workflow ID (e.g., `process-<md5hash>`).
- **Unchanged Files:** If a file hasn't changed, DBOS detects the existing successful workflow ID and returns the cached result immediately (0 cost).
- **Failed Files:** If a specific file failed previously, DBOS retries only that file.
- **Changed Files:** If a file is modified, its hash changes, triggering a new workflow execution.

### 2. Safety Check (Data Integrity)
To prevent "zombie" workflows (e.g., manual retries of old failures) from overwriting newer data, `save_step` includes a mandatory check:
- It verifies that the file on disk **still matches the hash** being processed.
- If the file has changed on disk during processing, the save is aborted to prevent inconsistent state.

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
