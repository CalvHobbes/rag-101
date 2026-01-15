import asyncio
import os
import sys
import time
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 1. Define server parameters
    # We use the same command as 'make mcp'
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "python", "scripts/run_mcp_server.py"],
        env=os.environ.copy()  # Pass current env (includes PYTHONPATH if set)
    )

    print(f"🔌 Connecting to MCP server...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 2. Initialize
            await session.initialize()
            
            # 3. List tools to verify connection
            tools = await session.list_tools()
            print(f"✅ Connected! Found {len(tools.tools)} tools: {[t.name for t in tools.tools]}")
            
            # 4. Call query_rag tool
            query = "What is RAG?"
            print(f"\n❓ Sending query: '{query}'")
            print("⏳ Waiting for response (this includes retrieval + generation)...")
            
            start_time = time.time()
            try:
                # FastMCP tools are called by name with keyword arguments
                result = await session.call_tool(
                    "query_rag",
                    arguments={"query": query, "top_k": 3}
                )
                end_time = time.time()
                duration = end_time - start_time
                
                # 5. Output results
                print(f"\n🚀 Response received in {duration:.2f} seconds!")
                
                # Content is usually a list of TextContent or ImageContent
                for content in result.content:
                    if content.type == "text":
                        print("\n--- Answer ---")
                        print(content.text)
                    else:
                        print(f"\n[Non-text content: {content.type}]")
                        
            except Exception as e:
                print(f"\n❌ Tool call failed: {e}")

if __name__ == "__main__":
    # Ensure PYTHONPATH includes the current directory so src imports work in the server
    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
    asyncio.run(main())
