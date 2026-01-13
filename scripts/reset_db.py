import asyncio
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.db.db_manager import db_manager
from src.models.base import Base
# Import models to ensure they are registered
from src.models.chunk import Chunk
from src.models.source_document import SourceDocument

async def cleanup():
    print("Dropping all tables...")
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("Tables dropped.")

    print("Re-initializing DB...")
    await db_manager.init_db()
    print("DB Reset Complete.")

if __name__ == "__main__":
    asyncio.run(cleanup())
