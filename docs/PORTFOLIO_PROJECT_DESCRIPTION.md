# ELETTRO Sales Intelligence Platform — Portfolio Project Description

Use or adapt the text below for your portfolio website (project card, case study, or “Projects” section).

---

## Short version (1–2 sentences)

**ELETTRO Intelligence** is a full-stack sales analytics platform for Indian B2B manufacturers. It provides real-time dashboards, geographic and material-level insights, risk views, and industrial PDF reports—powered by a Next.js frontend, FastAPI backend, and Supabase (PostgreSQL).

---

## Medium version (paragraph, ~150 words)

**ELETTRO Sales Intelligence Platform** is a cloud-ready analytics dashboard built for manufacturing sales teams. I designed and implemented a **Next.js 16** frontend and **FastAPI** backend that connect to **Supabase (PostgreSQL)** for multi-tenant sales data. Users get an **Executive Summary**, **Sales & Growth**, **Customer Intelligence**, and **Material Performance** dashboards with shared date/tenant filters. **Geographic Intelligence** uses an India state-level map; **Risk Management** highlights exposure; and **Industrial Reporting** generates downloadable PDFs. A **Cloud Data Uploader** ingests CSV into the database, and an in-app **AI chatbot** answers natural-language questions about the data. The app includes **role-based login**, **keyboard shortcuts**, and a **global filter bar** for consistent slicing across views. Stack: Next.js, React 19, Tailwind CSS, Recharts, Leaflet (maps), FastAPI, Pandas, SQLAlchemy, FPDF. Deployable on Vercel + Render with environment-based API and database configuration.

---

## Detailed version (for case study or project page)

### Project name
**ELETTRO Intelligence — Sales Analytics Platform**

### One-liner
Full-stack, multi-tenant sales intelligence dashboard for Indian manufacturers: dashboards, maps, risk views, PDF reports, and an AI assistant.

### Problem
Sales and leadership needed a single place to see performance by region, customer, and product (material), with the ability to upload data, run reports, and ask questions in plain language—without depending on spreadsheets or separate tools.

### Solution
A web app that combines:

- **Dashboards:** Executive summary, sales growth, customer intelligence, material performance (with treemap/bar views).
- **Geographic view:** India state-level map for regional performance.
- **Risk view:** Focused view on exposure and anomalies.
- **Data operations:** Cloud upload of CSV with validation and sync to PostgreSQL.
- **Reporting:** Industrial-style PDF reports (configurable, with branding).
- **AI assistant:** In-app chatbot that answers questions about the data using the same API.
- **Auth & UX:** Login, tenant-aware data, global filters (date range, states, customers, materials), and keyboard shortcuts.

### Tech stack

| Layer | Technologies |
|-------|----------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Tailwind CSS, Recharts, Leaflet (India map), Radix UI |
| **Backend** | FastAPI, Uvicorn, Pandas, SQLAlchemy, FPDF (PDF generation) |
| **Database** | PostgreSQL (Supabase), multi-tenant via `tenant_id` |
| **Auth** | Backend login endpoint; frontend AuthContext + session |
| **Deployment** | Vercel (frontend), Render (backend), Supabase (DB); Dockerfiles for backend and legacy app |

### What I did (role / highlights)

- **Full-stack ownership:** Designed and built the Next.js app and FastAPI API, including route structure, API client (`lib/api.ts`), and shared filter state.
- **Data model & API:** Multi-tenant schema, date-filtered queries, and aggregations for KPIs, customers, materials, and geography.
- **Visualization:** Interactive charts (Recharts), India state map (Leaflet + GeoJSON), and treemap/bar toggles for material views.
- **PDF reporting:** Server-side PDF generation (FPDF) with logos and tables, exposed via API for the Reports page.
- **AI integration:** Chat endpoint and widget that answer natural-language questions against the same dataset.
- **DevOps & structure:** Documented deployment (Vercel + Render), Dockerfiles for backend and legacy Streamlit app, and reorganized repo into `frontend/`, `backend/`, `legacy/`, and `docs/` for clarity.

### Outcomes

- Single platform for sales dashboards, geography, risk, and reports.
- Self-service data upload and consistent filtering across all views.
- Production-ready setup with env-based config and deployment docs.

### Links (fill in your own)

- **Live app:** [your-vercel-url]
- **API:** [your-render-url]
- **Repo:** [your-github-url]
- **Documentation:** See `docs/DEPLOYMENT.md` and `docs/STRUCTURE.md` in the repo.

---

## Bullet list (for project cards or CV)

- **ELETTRO Intelligence** — Full-stack sales analytics platform (Next.js, FastAPI, Supabase).
- Executive, Sales, Customer, and Material dashboards with shared filters and Recharts.
- India state-level geographic view (Leaflet + GeoJSON).
- Risk view and industrial PDF report generation (FPDF).
- Cloud CSV upload, multi-tenant PostgreSQL, and in-app AI chatbot.
- Auth, keyboard shortcuts, and deployment docs for Vercel + Render.

---

## Keywords (for SEO or filters)

Full-stack, Next.js, React, TypeScript, FastAPI, Python, PostgreSQL, Supabase, data visualization, dashboards, Recharts, Leaflet, PDF generation, multi-tenant, sales analytics, B2B, manufacturing, India.

---

*Copy the section that fits your portfolio (short, medium, or detailed) and replace placeholder links with your actual URLs.*
