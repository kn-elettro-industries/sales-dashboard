# Performance & optimization backlog

Prioritized improvements for the sales intelligence stack (FastAPI + Next.js + Postgres).

---

## Already in place (keep)

| Area | What |
|------|------|
| Data | `get_cached_tenant_df` + `TTLCache` — full tenant frame cached, date filters applied in memory |
| Egress | `EGRESS_MAX_YEARS` — optional SQL-side row limit on read |
| API | `GZipMiddleware` (≥500 bytes), 60s request timeout |
| Upload | Cache invalidation after new rows (`invalidate_tenant_cache`) |

---

## Quick wins (config / DB)

1. **Tenant cache tuning** — env vars (see `backend/api/db.py`):
   - `TENANT_CACHE_MAXSIZE` — default `10` (raise if you have more active tenants than 10).
   - `TENANT_CACHE_TTL_SECONDS` — default `14400` (4h); lower for fresher data, higher for less DB load.

2. **Indexes** — run once on Postgres (see `docs/sql/sales_master_indexes.sql`):
   - `(tenant_id)` and optionally `(tenant_id, date)` for filtered scans.

3. **Pool sizing** — if API workers > 1, watch `pool_size` / `max_overflow` in `get_engine()` vs Supabase connection limits.

---

## Backend code

| Idea | Why |
|------|-----|
| **Request-scoped df cache** | One HTTP handler calling `get_tenant_data` 10× still does 10× `DataFrame.copy()` from one cached load — cheap, but a `contextvars` cache per request could skip redundant copies for hot endpoints. |
| **Async offloading** | CPU-heavy pandas paths could use `run_in_executor` so the event loop stays responsive under parallel load (measure first). |
| **Structured logging** | `tenant_id`, `endpoint`, `duration_ms` on slow requests to find real bottlenecks. |
| **JWT** | Use timezone-aware `exp` (done in code); rotate `JWT_SECRET` in production. |

---

## Frontend

| Idea | Why |
|------|-----|
| **Single dashboard fetch** | Prefer one aggregated API response vs many parallel calls if latency dominates. |
| **SWR/React Query** | Dedupe + stale-while-revalidate for filter changes. |
| **Dynamic imports** | Heavy charts/maps only when the tab is visible. |

---

## Ops / security

| Idea | Why |
|------|-----|
| **CORS** | `main.py` stacks `CorsAllMiddleware` + `CORSMiddleware` — both allow `*`; consider one layer + explicit origins for production. |
| **Rate limits** | Login/upload endpoints — slow brute force / abuse. |
| **Secrets** | No default `JWT_SECRET` in production; use Render/Vercel env. |

---

## When to revisit architecture

- **Very large tables** per tenant → move from “load full DF then filter” to **SQL aggregations** for summary endpoints.
- **Multi-region** → read replicas, shorter TTL, or materialized views for KPIs.

---

*Last updated: engineering backlog — adjust priorities after profiling real traffic.*
