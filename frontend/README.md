# ELETTRO Intelligence — Sales Analytics Platform

Internal sales intelligence dashboard for K.N. Elettro Industries. Ingests invoice-level data, provides real-time analytics, and generates executive PDF reports.

## Stack

- **Frontend**: Next.js (App Router), TypeScript, Recharts, Vanilla CSS
- **Backend**: FastAPI, Python, Pandas, Matplotlib, fpdf2
- **Database**: Supabase (PostgreSQL)
- **Hosting**: Vercel (frontend) + Render (backend)

## Running Locally

```bash
# Backend — http://localhost:8000
cd backend
pip install -r requirements.txt
python main.py

# Frontend — http://localhost:3000
cd frontend
npm install
npm run dev
```

Set environment variables:
- `DATABASE_URL` — Supabase connection string
- `NEXT_PUBLIC_API_URL` — Backend API base URL (e.g. `http://localhost:8000/api`)

## Key Features

- Revenue & order KPIs with fiscal year filtering
- Customer RFM segmentation and risk heatmaps
- Product category performance & Pareto analysis
- India choropleth map for geographic revenue distribution
- Multi-format PDF report export (Executive Summary, Distributor Strategy, Category Report)
- AI chatbot for natural language data queries
- CSV/Excel data upload with auto-processing pipeline

## Project Layout

```
├── backend/
│   ├── main.py               # FastAPI app entry point
│   └── api/
│       ├── routes.py         # API endpoints
│       ├── db.py             # Supabase connection + TTL cache
│       ├── pdf_generator.py  # PDF report generation
│       └── chatbot.py        # AI chatbot query engine
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages
│       ├── components/ui/    # Shared UI components
│       └── lib/api.ts        # API client
└── assets/                   # Brand assets (logos)
```

## Notes

- PDF charts use `matplotlib.figure.Figure` directly — **never** `pyplot` (not thread-safe with Uvicorn)
- Multi-tenancy via `tenant_id` query parameter
- CORS exposes `Content-Disposition` header for PDF download filenames
- Proxy in `frontend/src/app/api/proxy/` forwards all backend calls to avoid CORS in production
