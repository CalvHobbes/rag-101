import contextlib
from typing import AsyncIterator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncConnection
from sqlalchemy.sql import text
from src.config import get_settings
from src.models.base import Base
# Import models so they are registered with Base metadata
from src.models.chunk import Chunk
from src.models.source_document import SourceDocument

class DatabaseManager:
    def __init__(self):
        self.settings = get_settings()
        # Ensure we use the async driver
        url = self.settings.database_url.replace("postgresql://", "postgresql+psycopg://")
        
        self.engine = create_async_engine(
            url,
            echo=False,
            pool_size=5,
            max_overflow=10
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            autoflush=False
        )

    async def init_db(self):
        """Initialize database: create extension and tables."""
        async with self.engine.begin() as conn:
            # 1. Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            # 2. Create all tables defined in Base
            await conn.run_sync(Base.metadata.create_all)

    @contextlib.asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        """Provide a transactional scope around a series of operations."""
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Global instance
db_manager = DatabaseManager()