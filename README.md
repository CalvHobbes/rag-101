# RAG Ingestion Pipeline

A production-aligned document ingestion pipeline for RAG systems.

## Quick Start

```bash
# Start Postgres
docker compose up -d

# Install dependencies
pip install -r requirements.txt

# Run ingestion
python scripts/run_ingestion.py --folder /path/to/docs
```

## Project Structure

```
src/
├── config.py           # pydantic-settings based config
├── exceptions.py       # Custom exception hierarchy
├── schemas/            # Pydantic validation schemas
├── models/             # SQLAlchemy database models
├── db/                 # Database setup
└── ingestion/          # Ingestion services
```
