import asyncio
import sys
from pathlib import Path

# Setup path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.retrieval.retriever import retrieve
from src.db.db_manager import db_manager

async def test_retrieval(query: str):
    print(f"\nQUERY: {query}")
    print("-" * 50)
    
    # Ensure DB is initialized (for the pool)
    # The retriever uses db_manager internally, so we just need to let it run.
    
    try:
        response = await retrieve(query, top_k=3, rerank=True)
        
        if not response.results:
            print("No results found.")
            return

        for i, result in enumerate(response.results):
            score = f"{result.similarity:.4f}"
            relevance = f"{getattr(result, 'relevance_score', 'N/A')}"
            
            print(f"\n[Result {i+1}]")
            print(f"Chunk ID: {result.chunk_id}")
            print(f"Similarity: {score} | Rerank Score: {relevance}")
            print(f"Source: {result.metadata.get('source', 'Unknown')}")
            print(f"Content:\n{result.content.strip()}")
            print("-" * 50)
            
    except Exception as e:
        print(f"Error during retrieval: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "What are 'Field Days' and why should you host them?"
        
    asyncio.run(test_retrieval(query))
