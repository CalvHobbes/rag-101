.PHONY: help install run test test-unit test-integration ingest demo mcp mcp-dev clean

# Default port for the API server
PORT ?= 8000

help:
	@echo "Available commands:"
	@echo "  make install         - Install dependencies with uv"
	@echo "  make run [PORT=8000] - Run the API server"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make ingest          - Run the ingestion pipeline"
	@echo "  make demo [QUERY=\"...\"] - Run the generation demo"
	@echo "  make mcp             - Run the MCP server (stdio)"
	@echo "  make mcp-dev         - Run MCP server with FastMCP inspector"
	@echo "  make clean           - Remove build artifacts and cache"

install:
	uv sync

run:
	uv run uvicorn src.api.main:app --reload --port $(PORT) $(ARGS)

test:
	uv run pytest

test-unit:
	uv run pytest tests/unit

test-integration:
	uv run pytest tests/integration

ingest:
	uv run scripts/run_ingestion.py

demo:
ifdef QUERY
	uv run scripts/generate_demo.py "$(QUERY)"
else
	uv run scripts/generate_demo.py
endif

mcp:
	PYTHONPATH="$(CURDIR)" uv run python scripts/run_mcp_server.py

mcp-dev:
	PYTHONPATH="$(CURDIR)" uv run fastmcp dev src/mcp/server.py:mcp

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
