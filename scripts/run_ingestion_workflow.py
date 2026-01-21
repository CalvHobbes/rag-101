"""
CLI entry point for DBOS-based ingestion workflow.

Usage:
    uv run python scripts/run_ingestion_workflow.py <folder_path>

Example:
    uv run python scripts/run_ingestion_workflow.py ./data/documents
"""
import asyncio
import sys
import uuid
from pathlib import Path

# Load environment variables BEFORE importing workflow module
from dotenv import load_dotenv
load_dotenv()

# Setup path so we can import src
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dbos import DBOS, SetWorkflowID
from src.ingestion.workflow import ingest_folder_workflow
from src.logging_config import configure_logging, get_logger
from src.config import get_settings

# Initialize logging
configure_logging(
    log_level=get_settings().log_level,
    json_format=get_settings().json_logs,
    log_file="ingestion_workflow.log"
)
log = get_logger(__name__)


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/run_ingestion_workflow.py <folder_path>")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    
    if not folder_path.exists():
        print(f"Error: Folder not found: {folder_path}")
        sys.exit(1)
    
    run_id = str(uuid.uuid4())[:8]
    
    log.info("workflow_starting", folder=str(folder_path), run_id=run_id)
    
    # Launch DBOS (initializes connection to system database)
    DBOS.launch()
    
    # Start the workflow with a unique ID for idempotency
    with SetWorkflowID(f"ingestion-{run_id}"):
        result = await ingest_folder_workflow(str(folder_path), run_id)
    
    log.info("workflow_complete", result=result)
    print(f"\nIngestion complete: {result}")


if __name__ == "__main__":
    asyncio.run(main())
