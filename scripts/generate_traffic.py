import asyncio
import os
import aiohttp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

QUESTIONS = [
    "What is RAG?",
    "How does the context window affect performance?",
    "Explain agentic workflows.",
    "What is the difference between RAG and fine-tuning?",
    "How do embeddings work?"
]

NEW_QUESTIONS = [
    "What are the top AI agent trends for 2026?",
    "How does context engineering improve RAG?",
    "Explain the future of AI agents according to Google Cloud.",
    "What are the best practices for context window management?",
    "Summarize the Weaviate ebook on context."
]

async def run_rest_query(session, query):
    url = "http://localhost:8000/query"
    try:
        async with session.post(url, json={"query": query, "top_k": 2}) as response:
            result = await response.json()
            print(f"[REST] Query: '{query}' -> Status: {response.status}")
            return result
    except Exception as e:
        print(f"[REST] Failed: {e}")

async def run_mcp_query(query):
    # Set up MCP client
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "scripts/run_mcp_server.py"],
        env=os.environ.copy()
    )
    
    # Ensure PYTHONPATH
    cwd = os.getcwd()
    if "PYTHONPATH" not in server_params.env:
         server_params.env["PYTHONPATH"] = cwd
    else:
         server_params.env["PYTHONPATH"] = f"{cwd}:{server_params.env['PYTHONPATH']}"

    print(f"[MCP] Connecting for query: '{query}'...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.list_tools()
                
                print(f"[MCP] Sending query: '{query}'")
                result = await session.call_tool(
                    "query_rag",
                    arguments={"query": query, "top_k": 2}
                )
                print(f"[MCP] Success for: '{query}'")
                return result
    except Exception as e:
        print(f"[MCP] Failed: {e}")

async def main():
    # 1. Run REST Queries
    print("--- Starting REST Queries ---")
    async with aiohttp.ClientSession() as session:
        for q in [ "Explain the future of AI agents according to Google Cloud."]:
            await run_rest_query(session, q)
            await asyncio.sleep(1) # small delay

    # # 2. Run MCP Queries
    # print("\n--- Starting MCP Queries ---")
    # for q in QUESTIONS:
    #     await run_mcp_query(q)
    #     await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
