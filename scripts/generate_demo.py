import asyncio
import logging
import opik
from src.generation.service import generate_answer
from src.schemas.generation import GenerateRequest
from src.schemas.retrieval import RetrievalFilter, FileType
from src.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)

import sys

async def main():
    # Default query
    query = "What is the architecture of the RAG system?"
    
    # Override if CLI arg provided
    if len(sys.argv) > 1:
        query = sys.argv[1]

    # 1. Run Query
    print(f"\n--- Processing Query: {query} ---")
    request = GenerateRequest(
        query=query,
        top_k=3,
        rerank=True
    )
    result = await generate_answer(request)
    print(f"\nQ: {result.query}")
    print(f"A: {result.answer}")
    print(f"Citations: {result.citations}")

    # 2. Filtered Query (Only run if using defaults/demo mode)
    if len(sys.argv) <= 1:
        print("\n--- Test 2: Filtered RAG (PDF only) ---")
        request_filtered = GenerateRequest(
            query="what are the key agent trends?",
            top_k=3,
            filter=RetrievalFilter(file_type=FileType.PDF)
        )
        result_filtered = await generate_answer(request_filtered)
        print(f"\nQ: {result_filtered.query}")
        print(f"A: {result_filtered.answer}")
        print(f"Citations: {result_filtered.citations}")

if __name__ == "__main__":
    asyncio.run(main())
