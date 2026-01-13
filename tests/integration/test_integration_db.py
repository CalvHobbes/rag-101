
import pytest
from sqlalchemy import text
from unittest.mock import patch, MagicMock
from src.db.db_manager import DatabaseManager
from src.config import get_settings, TimeoutSettings

@pytest.mark.asyncio
@pytest.mark.integration
async def test_db_query_timeout():
    """
    Integration Test: Verify that the database connection respects the configured command timeout.
    
    This test connects to the REAL database and runs a slow query.
    It requires the Docker database container to be running.
    """
    # Create valid settings with a short timeout
    real_settings = get_settings()
    
    # Create a new timeout settings object
    short_timeout = TimeoutSettings(
        llm_seconds=60.0,
        embedding_seconds=30.0,
        db_seconds=0.5  # 0.5s timeout!
    )
    
    # Mock the Settings object returned
    mock_settings = real_settings.model_copy(update={"timeout": short_timeout})

    # Patch where it is used in db_manager
    with patch("src.db.db_manager.get_settings", return_value=mock_settings):
        # Initialize a new manager. It will call get_settings() and get our mock
        db_mgr = DatabaseManager()
        
        try:
            async with db_mgr.get_session() as session:
                print("Running slow query (2s)...")
                # Run a query that takes 2.0 seconds
                # Timeout is 0.5 seconds
                await session.execute(text("SELECT pg_sleep(2.0)"))
                
            assert False, "Should have raised a timeout exception!"
            
        except Exception as e:
            print(f"Caught expected exception: {type(e).__name__}: {e}")
            error_str = str(e).lower()
            # psycopg raises QueryCanceled or OperationalError with message from PG
            assert "canceling statement due to statement timeout" in error_str, \
                f"Unexpected error message: {error_str}"
                
        finally:
            await db_mgr.engine.dispose()
