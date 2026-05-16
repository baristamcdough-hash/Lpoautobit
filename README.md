# Zero-Typing LPO Consolidator

A mobile-first web application that automates Local Purchase Order (LPO) consolidation for fresh produce procurement. Upload PDF purchase orders, and the system uses AI to extract, aggregate, and present a unified sourcing dashboard -- eliminating manual data entry for market runners.

## Architecture

```
+------------------+     +------------------+     +------------------+
|                  |     |                  |     |                  |
|   PDF Upload     +---->+   AI Parser      +---->+   SQLite DB      |
|   (Mobile/Web)   |     |   (OpenAI/       |     |   (Async         |
|                  |     |    Fallback)      |     |    SQLAlchemy)   |
+------------------+     +------------------+     +--------+---------+
                                                           |
                         +------------------+              |
                         |                  |              |
                         |   Dashboard      +<-------------+
                         |   (React SPA)    |
                         |                  |
                         +--------+---------+
                                  |
                         +--------v---------+
                         |                  |
                         |   CSV Export /   |
                         |   Google Sheets  |
                         |                  |
                         +------------------+
```

**Flow:** PDF Upload -> AI-powered Text Extraction -> Structured Data Storage -> Aggregated Dashboard & Export

## Quick Start (Docker)

The fastest way to run the full application:

```bash
# Clone the repository
git clone <repo-url>
cd Lpoautobit

# (Optional) Set your OpenAI API key for AI-powered extraction
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# Build and run with Docker Compose
docker compose up --build

# Access the app at http://localhost:8000
```

The application works without an OpenAI API key using a built-in regex fallback parser.

## Development Setup

### Backend (Python FastAPI)

```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Run the development server
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests
python3 -m pytest backend/tests/ -v
```

### Frontend (React + Vite)

```bash
# Install Node.js dependencies
cd client
npm install

# Run the development server (proxies /api to backend)
npm run dev

# Build for production
npm run build

# Run frontend tests
npm test
```

In development, the frontend dev server runs on port 5173 and proxies API requests to the backend on port 8000.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/lpo/upload` | Upload PDF files for LPO extraction |
| GET | `/api/lpo/raw-data` | Get all extracted line items (optional `?date_filter=YYYY-MM-DD`) |
| GET | `/api/lpo/dashboard` | Get aggregated procurement totals and distribution (optional `?date_filter=YYYY-MM-DD`) |
| PATCH | `/api/lpo/items/{item_id}/status` | Update procurement status of a line item |
| GET | `/api/lpo/export` | Export data as CSV (params: `format=csv`, `date=YYYY-MM-DD`, `type=raw\|picklist`) |

### Export Endpoint Details

```bash
# Export raw LPO data for today
curl http://localhost:8000/api/lpo/export?format=csv&type=raw

# Export consolidated pick list for a specific date
curl http://localhost:8000/api/lpo/export?format=csv&type=picklist&date=2024-01-15
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | No | - | OpenAI API key for AI-powered PDF extraction. System falls back to regex parsing if not set. |
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./backend/data/lpo.db` | Async database connection URL. |

## Production Integration Guide

### Google Drive Watching (via Make.com/Zapier)

1. Set up a watched folder in Google Drive where LPOs are uploaded
2. Create a Make.com/Zapier scenario that triggers on new files
3. The scenario should download the PDF and POST it to `/api/lpo/upload`
4. This enables zero-touch processing: drop a PDF in Drive, and it appears on the dashboard

### Google Sheets API

The export endpoint generates CSV files matching the LPO_Raw_Data and Marikiti_Pick_List tab structures. For direct Google Sheets write-back:

1. Create a Google Cloud project and enable the Sheets API
2. Create a service account and download credentials
3. Share your target spreadsheet with the service account email
4. Install `google-api-python-client` and use the Sheets API to write data
5. See `backend/services/sheets_export.py` for detailed integration code examples

### OpenAI API Key Setup

1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Generate an API key in Settings > API Keys
3. Set the key as the `OPENAI_API_KEY` environment variable
4. The system uses `gpt-4o-mini` for cost-effective extraction
5. Without a key, the system falls back to regex-based parsing (handles standard LPO formats)

## Mobile Usage

The app is designed mobile-first for market runners:

1. Open the app URL on your phone browser
2. **Add to Home Screen:** In your mobile browser menu, select "Add to Home Screen" for app-like access
3. **Upload:** Tap the Upload tab, select or photograph LPO PDFs
4. **Dashboard:** View the Marikiti Pick List with aggregated totals and per-customer breakdown
5. **Check off items:** Tap checkboxes as you procure each item at the market
6. **Export:** Download CSV files for record-keeping or sharing

The interface uses large tap targets, clear typography, and a bottom navigation bar optimized for one-handed phone use.

## Tech Stack

- **Backend:** Python 3.11, FastAPI, SQLAlchemy (async), aiosqlite, PyPDF2, OpenAI API
- **Frontend:** React 19, TypeScript, Vite, TailwindCSS v4, React Router, Axios, Lucide Icons
- **Testing:** pytest (backend), Vitest + Testing Library (frontend)
- **Deployment:** Docker multi-stage build, Docker Compose
- **Database:** SQLite (via aiosqlite for async access)
