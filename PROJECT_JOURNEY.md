# K.N. Elettro Intelligence Platform — Project Journey

> From a local Excel dashboard to a cloud-deployed SaaS platform.

---

## Phase 1: The Beginning (Jan 2026)
**Goal:** Replace manual Excel analysis with an automated dashboard.

### What Existed
- Sales team exported invoices from Tally as `.xlsx` files
- Monthly reports were made manually in Excel
- No centralized view of sales performance
- No GST analytics, no forecasting

### What Was Built
- **ETL Pipeline** (`etl_pipeline.py`) — Reads raw Excel files, standardizes column names, cleans data, merges customer master, calculates taxes (IGST/CGST/SGST)
- **Streamlit Dashboard** (`app.py`) — Interactive analytics with Plotly charts
- **Customer Master** — State/City mapping for GST zone classification
- **Exclusion Logic** — Filters out non-product materials (packaging, raw materials, etc.)

### Tech Stack (v1)
- Python + Pandas (data processing)
- Streamlit (frontend)
- SQLite (local database)
- Local file watcher for auto-ingest

---

## Phase 2: Branding & Analytics (Jan-Feb 2026)
**Goal:** Make the dashboard production-ready for the company.

### Changes
- **ELETTRO Branding** — Corporate gold theme, official logo, "Secure Intelligence Hub" login
- **Advanced Analytics** — Customer segmentation, RFM analysis, price elasticity
- **AI Chatbot (Krishiv)** — Natural language query interface for sales data
- **KPI Dashboard** — Revenue, invoices, AOV, top customers, state-wise breakdown
- **PDF Reports** — Auto-generated procurement and sales reports
- **User Authentication** — Login system with role-based access

### Analytics Modules Added
| Module | Purpose |
|---|---|
| `analytics/kpi.py` | Key performance indicators |
| `analytics/reporting.py` | Charts, tables, visualizations |
| `analytics/forecasting.py` | Prophet-based revenue prediction |
| `analytics/segmentation.py` | Customer clustering (RFM) |
| `analytics/chatbot.py` | AI-powered data Q&A |
| `analytics/quality.py` | Data quality scoring |
| `analytics/advanced.py` | Advanced analytics (Pareto, correlation) |

---

## Phase 3: SaaS Architecture (Feb 2026)
**Goal:** Decouple frontend and backend for cloud deployment.

### Architecture Shift
```
BEFORE (Local):
  Excel → File Watcher → ETL → SQLite → Streamlit (localhost)

AFTER (Cloud):
  Excel → Streamlit Upload → FastAPI → ETL → Supabase → Streamlit (internet)
```

### Changes
- **FastAPI Backend** (`backend/main.py`) — REST API for health checks, data retrieval, file uploads
- **PostgreSQL Migration** — Replaced SQLite with PostgreSQL (Supabase cloud)
- **Multi-Tenancy** — Added `tenant_id` to all queries for future SaaS support
- **In-Memory ETL** — Uploads processed without disk I/O (cloud-compatible)
- **API Fallback** — Dashboard tries direct DB, falls back to API

### New Files
- `backend/main.py` — FastAPI application
- `cloud_data_wrapper.py` — Cloud upload widget for Streamlit sidebar
- `docker-compose.yml` — Local dev with Docker PostgreSQL

---

## Phase 4: Cloud Deployment (Feb 27, 2026)
**Goal:** Make the platform accessible from anywhere.

### Infrastructure
| Service | Provider | URL |
|---|---|---|
| Database | Supabase (Sydney) | PostgreSQL cloud |
| API Backend | Render.com | https://sales-dashboard-wfay.onrender.com |
| Dashboard | Render.com | https://elettro-dashboard.onrender.com |
| Code | GitHub Org | github.com/kn-elettro-industries/sales-dashboard |

### Setup Steps Completed
1. Created Supabase project with PostgreSQL
2. Updated database connection with SSL mode
3. Created GitHub Organization (`kn-elettro-industries`)
4. Deployed FastAPI on Render (Python 3 web service)
5. Deployed Streamlit on Render (second web service)
6. Fixed cloud-specific issues:
   - In-memory file processing (no disk on Render)
   - Cloud-safe logging (FileHandler fallback)
   - API fallback in data loading
   - Duplicate data cleanup after multiple uploads

### Deployment Cost
| Item | Cost |
|---|---|
| Supabase Free Tier | Rs. 0/month |
| Render Free Tier (x2 services) | Rs. 0/month |
| GitHub Organization | Rs. 0/month |
| **Total** | **Rs. 0/month** |

---

## Phase 5: Folder Restructuring (Feb 27, 2026)
**Goal:** Clean up the codebase for long-term maintainability.

### Changes
- Deleted 7 temporary debug scripts
- Moved 5 batch files to `scripts/`
- Updated `.gitignore` for production
- Rewrote `README.md` with architecture docs
- Created this project journey document

---

## Data Scale

| Metric | Value |
|---|---|
| Excel files processed | 24 |
| Total sales records | 26,653 |
| Unique invoices | 9,032 |
| Total revenue tracked | Rs. 29.65 Crore |
| Date range | April 2024 — February 2026 |
| Customer states covered | 15+ |
| Product categories | 12+ |

---

## What's Next

| Priority | Feature | Status |
|---|---|---|
| 1 | Password hashing (security) | Planned |
| 2 | Self-signup for multi-tenant | Planned |
| 3 | Tally direct integration | Planned |
| 4 | WhatsApp daily reports | Planned |
| 5 | Mobile app (Flutter) | Prototype exists |
| 6 | Razorpay billing for SaaS | Planned |

---

*Document created: February 27, 2026*
*Author: K.N. Elettro Engineering Team*
