# LPO Consolidator

A fullstack application for consolidating Local Purchase Orders (LPOs) from multiple customers into a unified procurement dashboard.

## Backend

Python FastAPI backend with PDF upload, AI-powered parsing/extraction, SQLite database, and REST API endpoints.

### Setup

```bash
pip install -r backend/requirements.txt
```

### Run

```bash
uvicorn backend.main:app --reload
```

### Test

```bash
pytest backend/tests/ -v
```

## Sample PDFs

Generate sample LPO PDFs for testing:

```bash
python scripts/generate_sample_pdfs.py
```
