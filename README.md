# K.N. Elettro — Sales Intelligence Platform

A cloud-deployed sales analytics platform built for Indian manufacturers. Upload invoices, get instant dashboards with GST breakdowns, customer analytics, and revenue forecasting.

## Live URLs

| Service | URL |
|---|---|
| **Dashboard** | [elettro-dashboard.onrender.com](https://elettro-dashboard.onrender.com) |
| **API** | [sales-dashboard-wfay.onrender.com](https://sales-dashboard-wfay.onrender.com) |

## Architecture

**Current (default):** Next.js dashboard + FastAPI API.

```
Browser
   ↓
Next.js (port 3000)  ←→  FastAPI (port 8000)
                                ↓
                       Supabase (PostgreSQL)
```

**Legacy (optional):** Streamlit dashboard can run alongside; it uses the same FastAPI backend and DB.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | **Next.js** (primary); Streamlit (legacy, optional) |
| Backend API | FastAPI + Uvicorn (port 8000) |
| Database | Supabase (PostgreSQL) |
| ETL | Pandas + Custom Pipeline (backend upload + legacy script) |
| Analytics | Prophet, Scikit-learn, Plotly (legacy); Recharts (Next.js) |
| Hosting | Render.com (Free Tier) |

## Project Structure

See **STRUCTURE.md** for the full layout. Summary:

```
├── frontend/             # Next.js dashboard (current UI)
├── backend/              # FastAPI API (current backend)
├── legacy/               # Old Streamlit app (app.py, analytics/, …)
├── docs/                 # DEPLOYMENT.md, PDF, engineering_journal
├── assets/               # Logos, CSS
├── data/                 # Data files (gitignored)
├── scripts/              # Utility scripts
├── docker-compose.yml    # Postgres (optional local)
└── README.md
```

## Local Development

**Current stack (Next.js + FastAPI):**

```bash
# 1. Backend (port 8000)
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

# 2. Frontend (port 3000) — in another terminal
cd frontend
npm install
npm run dev
```

- Dashboard: **http://localhost:3000**
- API docs: **http://localhost:8000/docs**

**Legacy Streamlit app (optional):** runs on port 8501. Use the same FastAPI backend (8000); do not start a second backend.

```bash
cd legacy
pip install -r requirements.txt
streamlit run app.py
```

Or from repo root: `streamlit run legacy/app.py`

## Auth & Default Login

Create a default admin user for local development:

```bash
python scripts/seed_admin.py
```

**Default credentials (after seeding):**
- Username: `admin`
- Password: `admin123`

Or sign up at `/signup` to create your own account.

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string (backend + legacy ETL) |
| `API_URL` | FastAPI base URL (legacy Streamlit, e.g. `http://localhost:8000`) |
| `NEXT_PUBLIC_API_URL` | Full API base for Next.js (e.g. `http://localhost:8000/api`). Defaults to `http://localhost:8000/api` if unset. |

## Deploy

- **Quick path:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Render (backend) + Vercel (frontend).
- **Full options:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — VPS, Docker, CORS, env vars.
- Repo root **render.yaml** can be used for a Render Blueprint (backend only).

## License

Proprietary — K.N. Elettro Industries
