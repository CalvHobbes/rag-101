"""Demo script for testing retrieval queries."""
import asyncio
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.retrieval import retrieve
from src.schemas.retrieval import RetrievalFilter


async def main():
    """Test the full retrieval pipeline with a sample query."""
    query = "what is the rag 101 project about?"
    query = "what is context window?"
    print(f"Query: {query}")
    print("-" * 60)
    # metadata_filter=RetrievalFilter(source="/Users/priya/Documents/tech/rag 101/test_docs/google_cloud_ai_agent_trends_2026_report.pdf")
    metadata_filter = None #RetrievalFilter(file_type="txt")
    
    # response = await retrieve(query, top_k=3, distance_threshold=0, 
    # metadata_filter=metadata_filter)
    response = await retrieve(query, top_k=3, rerank=True)
    
    print(f"Results found: {response.result_count}")
    print()
    
    for i, r in enumerate(response.results, 1):
        print(f"{i}. Similarity: {r.similarity:.4f}")
        print(f"   File: {r.file_path}")
        print(f"   Content: {r.content[:80]}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
