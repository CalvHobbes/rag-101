"""Schemas for ingestion workflow API."""
from pydantic import BaseModel, Field
from typing import Optional


class IngestRequest(BaseModel):
    """Request to start an ingestion workflow."""
    folder_path: str = Field(..., description="Path to folder to ingest")


class IngestResponse(BaseModel):
    """Response after starting an ingestion workflow."""
    workflow_id: str
    status: str  # "started", "running", "complete", "failed"
    message: str


class WorkflowStatusResponse(BaseModel):
    """Response for workflow status check."""
    workflow_id: str
    status: str
    files_found: Optional[int] = None
    files_processed: Optional[int] = None
    files_skipped: Optional[int] = None
    result: Optional[dict] = None