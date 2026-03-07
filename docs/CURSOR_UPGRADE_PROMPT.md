# ELETTRO Intelligence — Cursor Upgrade Prompt

## Project Overview

**ELETTRO Intelligence** is a full-stack enterprise sales analytics dashboard for **K.N. Elettro Industries**, an Indian industrial electrical components manufacturer. It ingests invoice-level sales data (CSV/Excel), stores it in **Supabase (PostgreSQL)**, and presents interactive dashboards, AI chatbot insights, geographic heatmaps, and downloadable PDF reports.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16 (App Router), TypeScript, Recharts, Lucide Icons, Vanilla CSS |
| **Backend** | Python 3, FastAPI (Uvicorn), Pandas, FPDF, Matplotlib (thread-safe Figures) |
| **Database** | Supabase (PostgreSQL) — cloud-hosted at `aws-1-ap-southeast-2.pooler.supabase.com:6543` |
| **Caching** | `cachetools.TTLCache` — tenant DataFrames cached in-memory for 1 hour |
| **Auth** | Tenant-based multi-tenancy via `tenant_id` column in `sales_master` table |
| **PDF Engine** | FPDF + Matplotlib `Figure` objects (NOT pyplot — pyplot deadlocks Uvicorn) |

---

## Project Structure

```
sales_pipeline (EXPERIMENT)/
├── backend/
│   ├── main.py                  # FastAPI app entry, CORS config, Uvicorn startup
│   └── api/
│       ├── __init__.py
│       ├── routes.py            # All API endpoints (metrics, charts, filters, reports, upload, chat)
│       ├── db.py                # Supabase connection, get_tenant_data(), TTL cache, update_database()
│       ├── pdf_generator.py     # PDF report builder (FPDF + Matplotlib Figure, ~685 lines)
│       └── chatbot.py           # AI chatbot query processor (gemini-based)
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx             # Executive Summary dashboard (home)
│   │   │   ├── layout.tsx           # Root layout with Sidebar + FilterProvider + GlobalFilterBar
│   │   │   ├── sales/page.tsx       # Sales & Growth page
│   │   │   ├── customers/page.tsx   # Customer Intelligence page
│   │   │   ├── materials/page.tsx   # Material Performance page
│   │   │   ├── geographic/page.tsx  # Geographic Intelligence (India choropleth map)
│   │   │   ├── risk/page.tsx        # Risk Management page
│   │   │   ├── data/page.tsx        # Cloud Data Uploader page
│   │   │   └── reports/page.tsx     # Industrial Reporting (tabbed: Interactive + PDF Export)
│   │   ├── components/
│   │   │   ├── FilterContext.tsx     # Global filter state (tenant, dateRange, states, cities, etc.)
│   │   │   └── ui/
│   │   │       ├── Sidebar.tsx       # Navigation sidebar
│   │   │       ├── GlobalFilterBar.tsx # Top filter bar (region, time, advanced filters)
│   │   │       ├── KpiCard.tsx       # KPI metric card component
│   │   │       ├── Charts.tsx        # Recharts wrappers (AreaChart, PieChart, BarChart)
│   │   │       ├── DataTable.tsx     # Sortable, searchable, paginated data table
│   │   │       ├── IndiaMap.tsx      # SVG choropleth map of India
│   │   │       └── ChatWidget.tsx    # Floating AI chatbot widget
│   │   └── lib/
│   │       └── api.ts               # API client functions (fetchKpiSummary, fetchAllCustomers, etc.)
│   ├── package.json
│   └── next.config.ts
├── assets/
│   └── logo.png, logo_transparent.png
├── data/                            # Local CSV data files (legacy)
├── analytics/                       # Legacy Streamlit analytics modules
├── app.py                           # Legacy Streamlit app (not used by Next.js frontend)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Backend API Endpoints (FastAPI — `routes.py`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/metrics/summary` | KPI summary (revenue, orders, customers, avg order value) |
| GET | `/api/charts/trend` | Monthly sales trend data |
| GET | `/api/charts/top-customers` | Top N customers by revenue |
| GET | `/api/charts/material-groups` | Material group revenue breakdown |
| GET | `/api/filters/options` | Available filter options (states, cities, FYs, months) |
| GET | `/api/customers/all` | All customers with revenue |
| GET | `/api/customers/rfm` | RFM segmentation analysis |
| GET | `/api/materials/performance` | Material performance metrics |
| GET | `/api/materials/pareto` | Pareto analysis (80/20 rule) |
| GET | `/api/geographic/states` | State-wise revenue data |
| GET | `/api/geographic/cities` | City-wise revenue data |
| GET | `/api/risk/analysis` | Customer risk analysis |
| GET | `/api/reports/download` | **PDF report generator** (takes ~15-30s for full dataset) |
| GET | `/api/reports/item-details` | Item-level aggregated data for interactive reports |
| POST | `/api/upload` | CSV/Excel data upload pipeline |
| POST | `/api/chat` | AI chatbot query processing |

All endpoints accept `tenant_id` + optional filter params (`start_date`, `end_date`, `states`, `cities`, `customers`, `material_groups`, `fiscal_years`, `months`).

---

## Database Schema

Single table: `sales_master` in Supabase PostgreSQL

| Column | Type | Description |
|--------|------|-------------|
| tenant_id | text | Multi-tenant identifier |
| DATE | timestamp | Invoice date |
| INVOICE_NO | text | Invoice number |
| CUSTOMER_NAME | text | Customer name |
| CITY | text | City |
| STATE | text | State/Region |
| ITEMNAME | text | Product/Item name |
| ITEM_NAME_GROUP | text | Material group category |
| MATERIALGROUP | text | Broader material group |
| QUANTITY | numeric | Quantity sold |
| AMOUNT | numeric | Revenue amount (INR) |
| FINANCIAL_YEAR | text | Fiscal year (e.g., "FY24-25") |
| MONTH | text | Month abbreviation (e.g., "FEB-26") |

Default tenant: `default_elettro` (~26,761 rows)

---

## Current Design & Theme

- **Color scheme**: Dark mode with gold (#DAA520 / #FFD700) accents on near-black (#161B22, #212529) backgrounds
- **Typography**: System fonts (Arial/sans-serif)
- **Branding**: "ELETTRO INTELLIGENCE" with company logo
- **Currency**: Indian Rupees (₹ / Rs.)
- **Fiscal Year**: April–March (Indian FY standard)

---

## Known Issues & Bugs to Fix

1. **PDF Generation is slow** (~15-30 seconds) — Matplotlib chart rendering on 26K+ rows is CPU-intensive. Consider reducing chart DPI, limiting data points, or generating charts asynchronously.

2. **"All Time" filter sometimes shows zeros on fresh load** — Intermittent race condition where the dashboard renders before the first API response arrives.

3. **Global Filter Bar "Export Data" button is not connected** — The "Export Data" button in `GlobalFilterBar.tsx` has no download functionality wired up.

4. **PDF report shows "No data available" when restrictive filters are active** — The PDF download passes ALL global filter bar selections. If the user has a very specific combination (e.g., one customer + one month), it can result in zero rows.

5. **Recharts warnings** — `width(-1) and height(-1)` warnings appear in the console because charts render before their container has dimensions.

6. **Next.js hydration mismatch warning** — Minor SSR/client mismatch (non-critical).

---

## Critical Technical Constraints

> ⚠️ **NEVER use `matplotlib.pyplot` (plt) in the backend.** The global pyplot state machine is NOT thread-safe and will deadlock Uvicorn's event loop. Always use `matplotlib.figure.Figure` and `matplotlib.backends.backend_agg.FigureCanvasAgg` directly.

> ⚠️ **NEVER use `pandas.DataFrame.plot()`** — it internally calls pyplot and causes the same deadlock.

> ⚠️ **Supabase connection uses `pool_pre_ping=True`** — The database is cloud-hosted, connections may drop after idle periods. The pool handles reconnection automatically.

> ⚠️ **CORS is configured with `expose_headers=["Content-Disposition"]`** — Required for PDF download filenames to work correctly in the browser.

---

## Upgrade Roadmap — What to Build Next

### 🔴 Priority 1: Performance & Reliability

- [ ] **Async PDF generation** — Move PDF generation to a background task queue (e.g., Celery/Redis or `asyncio.to_thread`). Return a job ID immediately, let the frontend poll for completion.
- [ ] **Reduce PDF render time** — Lower chart DPI from 300 to 150, limit data series to top 20, skip charts if <5 data points.
- [ ] **Add request timeout middleware** — Prevent any single request from blocking the server for >60 seconds.
- [ ] **Fix "All Time" race condition** — Add loading skeleton states and ensure the first API call completes before rendering charts.

### 🟡 Priority 2: Feature Upgrades

- [ ] **User Authentication** — Add JWT-based auth with login/signup pages. Currently there is no authentication — any user can access any tenant's data.
- [ ] **Role-Based Access Control (RBAC)** — Admin vs. Viewer roles.
- [ ] **Email scheduled reports** — Allow users to schedule daily/weekly/monthly PDF reports via email (needs SMTP integration).
- [ ] **Real-time notifications** — WebSocket-based alerts for new data uploads or threshold breaches.
- [ ] **Advanced Analytics Dashboard** — Add forecasting (ARIMA/Prophet), ABC analysis, seasonal decomposition.
- [ ] **Connect "Export Data" button** — Wire up the global filter bar's Export Data button to download filtered data as CSV/Excel.

### 🟢 Priority 3: UI/UX Polish

- [ ] **Loading skeletons** — Replace all "Loading..." text with shimmer skeleton animations.
- [ ] **Dark/Light mode toggle** — Add a theme switcher.
- [ ] **Mobile responsive** — Current layout breaks below 1024px. Add responsive breakpoints.
- [ ] **Animated transitions** — Add page transition animations and chart entry animations.
- [ ] **Better error handling** — Show toast notifications for API errors instead of console.error.
- [ ] **Breadcrumb navigation** — Add breadcrumbs for deeper navigation context.

### 🔵 Priority 4: DevOps & Deployment

- [ ] **Docker Compose for full stack** — current Dockerfile only covers the legacy Streamlit app. Create a proper compose with FastAPI + Next.js + Nginx.
- [ ] **CI/CD pipeline** — GitHub Actions for automated testing and deployment.
- [ ] **Environment-based config** — Proper .env handling for dev/staging/production.
- [ ] **Database migrations** — Add Alembic for schema versioning instead of raw `to_sql()`.
- [ ] **API rate limiting** — Protect public endpoints.
- [ ] **Monitoring & logging** — Add structured logging (e.g., structlog) and APM (e.g., Sentry).

---

## How to Run

```bash
# Backend (FastAPI)
cd backend
pip install -r ../requirements.txt
py main.py
# Runs on http://localhost:8080

# Frontend (Next.js)
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

---

## Important Files to Review First

1. `backend/api/routes.py` — All API logic (~484 lines)
2. `backend/api/db.py` — Database connection & caching (~125 lines)
3. `backend/api/pdf_generator.py` — PDF report builder (~685 lines)
4. `frontend/src/components/FilterContext.tsx` — Global state management
5. `frontend/src/lib/api.ts` — API client
6. `frontend/src/app/page.tsx` — Main dashboard page
7. `frontend/src/app/reports/page.tsx` — Reports page (tabbed interface)
8. `frontend/src/components/ui/GlobalFilterBar.tsx` — Top filter bar

---

*Generated on 05 March 2026 for ELETTRO Intelligence v1.0 — K.N. Elettro Industries*
