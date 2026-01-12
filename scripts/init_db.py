import asyncio
import sys
from pathlib import Path

# Add project root to python path to allow imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.db.db_manager import db_manager

async def main():
    print("Initializing Database...")
    try:
        await db_manager.init_db()
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
