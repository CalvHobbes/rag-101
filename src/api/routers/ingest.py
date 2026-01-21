"""
Ingest endpoint for triggering DBOS workflows via REST API.
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException

from dbos import DBOS, SetWorkflowID
from src.schemas.ingest import IngestRequest, IngestResponse, WorkflowStatusResponse
from src.ingestion.workflow import ingest_folder_workflow
from src.logging_config import get_logger

log = get_logger(__name__)

router = APIRouter(prefix="/ingestfolder", tags=["Ingest"])


@router.post("", response_model=IngestResponse)
async def start_ingest(request: IngestRequest) -> IngestResponse:
    """
    Start an async ingestion workflow for a folder.
    Returns immediately with a workflow ID for status polling.
    """
    folder_path = Path(request.folder_path)
    
    if not folder_path.exists():
        raise HTTPException(status_code=400, detail=f"Folder not found: {folder_path}")
    
    if not folder_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {folder_path}")
    
    run_id = str(uuid.uuid4())[:8]
    workflow_id = f"ingestion-{run_id}"
    
    log.info("workflow_starting_via_api", folder=str(folder_path), workflow_id=workflow_id)
    
    # Start workflow asynchronously (returns handle, doesn't wait)
    with SetWorkflowID(workflow_id):
        # DBOS.start_workflow returns immediately with a handle (non-blocking)
        handle = DBOS.start_workflow(ingest_folder_workflow, str(folder_path), run_id)
    
    return IngestResponse(
        workflow_id=workflow_id,
        status="started",
        message=f"Ingestion started for {folder_path.name}"
    )


@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str) -> WorkflowStatusResponse:
    """
    Get the status of an ingestion workflow.
    """
    try:
        handle = DBOS.retrieve_workflow(workflow_id)
        status = handle.get_status().status  # WorkflowStatus.status = PENDING, SUCCESS, ERROR, etc.
        
        # Try to get result if complete
        result = None
        if status == "SUCCESS":
            result = handle.get_result()  # Synchronous - blocks until complete
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status,
            files_found=result.get("files_found") if result else None,
            files_processed=result.get("files_processed") if result else None,
            files_skipped=result.get("files_skipped") if result else None,
            result=result
        )
    except Exception as e:
        log.error("workflow_status_error", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}")