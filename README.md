# K.N. Elettro — Sales Intelligence Platform

A cloud-deployed sales analytics platform built for Indian manufacturers. Upload invoices, get instant dashboards with GST breakdowns, customer analytics, and revenue forecasting.

## Live URLs

| Service | URL |
|---|---|
| **Dashboard** | [elettro-dashboard.onrender.com](https://elettro-dashboard.onrender.com) |
| **API** | [sales-dashboard-wfay.onrender.com](https://sales-dashboard-wfay.onrender.com) |

## Architecture

```
Browser (Anywhere)
    ↓
Render: Streamlit Dashboard  ←→  Render: FastAPI API
                                        ↓
                               Supabase (PostgreSQL)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| ETL | Pandas + Custom Pipeline |
| Analytics | Prophet, Scikit-learn, Plotly |
| Hosting | Render.com (Free Tier) |

## Project Structure

See **STRUCTURE.md** for the full layout. Summary:

```
├── frontend/             # Next.js dashboard (current UI)
├── backend/              # FastAPI API (current backend)
├── legacy/               # Old Streamlit app (app.py, analytics/, …)
├── docs/                 # DEPLOYMENT.md, DEPLOY-TOMORROW.md, PDF, engineering_journal
├── assets/               # Logos, CSS
├── data/                 # Data files (gitignored)
├── scripts/              # Utility scripts
├── docker-compose.yml    # Postgres (optional local)
└── README.md
```

## Local Development

**Current stack (Next.js + FastAPI):**

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# Frontend (another terminal)
cd frontend && npm install && npm run dev
```

**Legacy Streamlit app (optional):**

```bash
cd legacy && pip install -r requirements.txt && streamlit run app.py
```

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `API_URL` | FastAPI backend URL |

## License

Proprietary — K.N. Elettro Industries
