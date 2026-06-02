# KN Elettro — Sales Intelligence Platform

A cloud-deployed sales analytics platform built for KN Elettro Industries. Upload daily invoices, get instant dashboards with geographic intelligence, customer analytics, product mix analysis, and PDF reporting.

## Live

| Service | URL |
|---|---|
| **Dashboard** | [sales-dashboard-eight-xi.vercel.app](https://sales-dashboard-eight-xi.vercel.app) |
| **Backend API** | Render (auto-deploy on push to `main`) |

## Architecture

```
Browser
   ↓
Next.js — Vercel
   ↓  (proxy /api/*)
FastAPI — Render
   ↓
PostgreSQL (Neon)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS v4, Recharts |
| Backend | FastAPI, Uvicorn, Pandas, SQLAlchemy |
| Database | PostgreSQL (Neon) |
| Hosting | Vercel (frontend) + Render (backend) |
| PDF Reports | fpdf2 |
| Auth | JWT (bcrypt) |

## Features

- **Executive Dashboard** — KPI cards with sparklines, revenue trend, material group donut, top customers
- **Sales & Growth** — Monthly/daily trend charts, MoM growth %, monthly breakdown table
- **Customer Intelligence** — RFM segmentation, scatter bubble chart with quadrant shading, segment colours
- **Material Performance** — Treemap with drilldown to individual items, Pareto/ABC curve chart
- **Geographic Intelligence** — Interactive India choropleth map, state → city → customer drilldown
- **Risk Management** — Revenue concentration, inactive customers, single-order customers
- **PDF Reports** — Executive summary, distributor strategy, dynamic reports with FY comparison tables
- **AI Chatbot** — 15-intent rule-based engine with fuzzy customer/product matching
- **Cloud Data Uploader** — Daily sales upload (CSV/Excel), customer master linking, data quality health score
- **Industrial Reporting** — Distributor vs target tracking

## Local Development

```bash
# 1. Backend (port 8000)
cd backend
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend (port 3000) — separate terminal
cd frontend
npm install
npm run dev
```

- Dashboard: **http://localhost:3000**
- API docs: **http://localhost:8000/docs**

## Environment Variables

### Backend (Render)
| Variable | Description |
|---|---|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `JWT_SECRET` | Secret key for JWT signing (set a strong value in production) |
| `TENANT_CACHE_TTL_SECONDS` | Tenant DataFrame cache TTL; default `14400` (4h) |
| `EGRESS_MAX_YEARS` | Limit DB read to last N years; `0` = load all (default) |

### Frontend (Vercel)
| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | FastAPI base URL, e.g. `https://your-backend.onrender.com/api` |

## Data Upload Workflow

1. Go to **Cloud Data Uploader** in the sidebar
2. Upload **Customer Master** first (columns: `CUSTOMER_NAME`, `STATE`, `CITY`) — saved to DB permanently
3. Upload daily sales Excel/CSV files — STATE/CITY is auto-enriched from the customer master at query time
4. Refresh any page — geographic data updates immediately

## Auth

Signup is disabled by default. Create users via:

```bash
python scripts/seed_admin.py              # creates admin / admin123
python scripts/seed_admin.py add <user> <password>
```

Set `SIGNUP_ENABLED=true` in Render env to open public signup.

## Deployment

- **Frontend**: Push to `main` → Vercel auto-deploys
- **Backend**: Push to `main` → Render auto-deploys
- See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full setup

## License

Proprietary — KN Elettro Industries
