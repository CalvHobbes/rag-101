# DBOS + Opik Tracing: Investigation & Solution

## Goal

Achieve unified tracing for DBOS ingestion workflows in Opik, with a single trace tree showing the complete workflow hierarchy.

---

## Investigation Summary

We explored multiple approaches to trace DBOS workflows in Opik. This document records our findings.

### Approach 1: DBOS OTLP + Opik SDK Hybrid (Failed)

**Hypothesis:** Use DBOS's built-in OTel export to send workflow/step spans to Opik, then inject the OTel trace context into Opik SDK spans to create a unified tree.

**Implementation:**
1. Enabled DBOS OTLP export (`enable_otlp=True`) pointing to Opik's OTel endpoint
2. Modified `@track` decorator to extract OTel context and pass it via `opik_distributed_trace_headers`
3. Created trace records via Opik's client API to ensure parent traces existed

**Failure Reason: Dual Trace ID Generation**

DBOS generates **two different trace IDs**:
- **OTLP Export Trace ID**: e.g., `019be202-572d-...` (UUIDv7)
- **OTel Context Trace ID**: e.g., `0d1b8bf2-2c7f-...` (128-bit hex)

These are **completely different**, resulting in two parallel trace trees in Opik instead of one unified tree.

---

## Final Solution: Opik SDK Only

**Chosen Approach:** Disable DBOS OTLP export and use only Opik's `@track` decorator on all workflows and steps.

**Why This Works:**
- All spans flow through a single tracing system (Opik SDK)
- Python's `contextvars` propagate correctly within the same process
- DBOS still provides durability, but tracing is handled by Opik

**Configuration:**

```bash
# .env
DBOS_OTLP_ENABLED=false
```

**Decorator Pattern:**

```python
# Top-level workflow gets the phase + execution tag
@DBOS.workflow()
@track(name="ingest_folder_workflow", phase=Phase.INGESTION, tags=["execution:workflow"])
async def ingest_folder_workflow(...):

# Child workflows and steps get no phase (helpers)
@DBOS.workflow()
@track(name="process_file_workflow")
async def process_file_workflow(...):

@DBOS.step()
@track(name="embed_step")
async def embed_step(...):
```

**Result:** Single unified trace tree:
```
INGESTION (ingest_folder_workflow) [execution:workflow]
 ├── discover_files_step
 └── process_file_workflow
      ├── check_exists_step
      ├── load_and_normalize_step → load_document
      ├── chunk_step → chunk_documents
      ├── embed_step → embed_documents
      └── save_step → save_documents
```

---

## Files Changed

| File | Change |
|------|--------|
| `.env` | `DBOS_OTLP_ENABLED=false` |
| `src/ingestion/workflow.py` | Added `@track` decorators with appropriate phases/tags |
| `src/observability.py` | Contains OTel context extraction (retained for future use) |

---

## Key Learnings

1. **DBOS OTel context ≠ DBOS OTLP traces** - They use different trace IDs
2. **Simpler is better** - Using one tracing system (Opik SDK) avoids correlation complexity
3. **Use tags for execution modes** - Distinguish `execution:workflow` vs `execution:manual` via tags, not phases
4. **Follow phase rules** - Only top-level orchestrators get `Phase.INGESTION`; helpers have no phase

