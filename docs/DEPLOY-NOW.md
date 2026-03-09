# Deploy Now — Next.js + FastAPI

Use this after code is pushed to GitHub. You need: **GitHub repo**, **Supabase** `DATABASE_URL`, and accounts on **Render** + **Vercel** (free tiers OK).

**What about Streamlit?** This repo used to have a **Streamlit** dashboard (Python UI for data apps). The live app is now **Next.js + FastAPI**. The old Streamlit app is in **`legacy/`** — you can run it locally with `streamlit run legacy/app.py` (port 8501); it talks to the same FastAPI backend. It is **not** deployed with the Vercel/Render setup below. See **§9** for deployment options; Streamlit can be deployed separately (e.g. Streamlit Community Cloud) if you want to keep using it.

**Use Streamlit for sharing and R&D:** You can run **Next.js** (Vercel) for production and **Streamlit** (deployed separately) for sharing with others and doing R&D in parallel. The backend already exposes **`/api/v1/data`** and **`/api/v1/upload_batch`** so the legacy Streamlit app works against the same Render API. See **§10 Deploy Streamlit** below.

---

## 1. Backend on Render

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
2. Connect your GitHub repo (`kn-elettro-industries/sales-dashboard` or your fork).
3. If the repo has a **render.yaml** at root:
   - You can use **New** → **Blueprint** and connect the repo; Render will create the service from `render.yaml`.  
   - Then open the service → **Environment** → add **DATABASE_URL** (your Supabase connection string).
4. If setting up manually, use **one** of these:

   **Option A (recommended – runs from repo root):**
   - **Root Directory:** leave **empty** (repo root)
   - **Build Command:** `cd backend && pip install -r requirements.txt`
   - **Start Command:** `sh start-backend.sh`
   - **Environment:** `DATABASE_URL` = Supabase URL; `PYTHON_VERSION` = `3.11.9`

   **Option B (root = backend):**
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `sh run.sh`
   - **Environment:** `DATABASE_URL` = Supabase URL; `PYTHON_VERSION` = `3.11.9`

   **If you get "cannot open run.sh":** Render may be running the start command from repo root. Then use: **Root Directory** = *(leave empty)*, **Build** = `cd backend && pip install -r requirements.txt`, **Start** = `sh backend/run.sh`.

5. Click **Create Web Service**. Wait for deploy.
6. Copy the service URL, e.g. `https://elettro-api-xxxx.onrender.com`.

**If deploy exits with status 1:** In Render → **Logs**, scroll to the line just before “Exited with status 1” to see the Python traceback. Set **PYTHON_VERSION** to **3.11.9** (full version) in Environment to avoid Python 3.14 issues.

---

## 2. Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import the same GitHub repo.
3. **Root Directory:** set to `frontend` (Override).
4. **Environment Variables:** Add:
   - `NEXT_PUBLIC_API_URL` = `https://YOUR-RENDER-URL/api` (e.g. `https://sales-dashboard-wfay.onrender.com/api` — no trailing space.)
   - **To avoid CORS issues:** set `NEXT_PUBLIC_USE_API_PROXY` = `true`. The app will call your own `/api/proxy`, which forwards to the Render backend server-side (no cross-origin requests from the browser). **Apply to Production, Preview, and Development** so branch/preview URLs (e.g. `*-commanderadis-projects.vercel.app`) also use the proxy.
5. Deploy. Copy your frontend URL, e.g. `https://sales-dashboard-xxx.vercel.app`.

---

## 3. CORS (or use the proxy)

**Recommended:** On Vercel, set `NEXT_PUBLIC_USE_API_PROXY=true`. The frontend then calls same-origin `/api/proxy`, which forwards to Render server-side — **no CORS** from the browser.

If you call the backend directly (no proxy), ensure the backend allows your origin (see `backend/main.py` CORS config). The repo already uses permissive CORS; if you still see "blocked by CORS policy", use the proxy above.

---

## 4. Database (Supabase)

- In Supabase: **Project Settings** → **Database** → **Connection string** (Transaction mode).
- Add `?sslmode=require` and use that as `DATABASE_URL` on Render.
- Ensure the **sales_master** table exists (the app creates/uses it; run a test upload if needed).

**Reducing Supabase egress (if over quota):** The backend caches tenant data for **4 hours** and invalidates on upload. To fetch less data per request, set on Render: **`EGRESS_MAX_YEARS`** = `3` (or `2`). The app will only load rows where `date` is within the last 3 (or 2) years, reducing data transfer. Leave unset to load all years.

---

## 5. Test

- Open your **Vercel** URL. Dashboard should load.
- Try filters, Geographic map, Reports, Data upload. All requests go to your Render backend.
- If you see "Failed to fetch", check: (1) `NEXT_PUBLIC_API_URL` has `/api` at the end, (2) CORS includes your Vercel URL, (3) Render service is not sleeping (free tier sleeps after inactivity).

---

## 6. No data on the dashboard?

**Two common causes:**

1. **Frontend not talking to the API**
   - In **Vercel** → your project → **Settings** → **Environment Variables**, add (or fix):
     - `NEXT_PUBLIC_API_URL` = `https://YOUR-RENDER-URL/api` (e.g. `https://sales-dashboard-wfay.onrender.com/api`).
   - **Redeploy** the frontend after changing env vars (NEXT_PUBLIC_* are baked in at build time).
   - In the browser, open DevTools → **Network** tab, refresh the dashboard. You should see requests to `https://...onrender.com/api/dashboard/summary`. If you see requests to `localhost`, the env is wrong or missing.

2. **Database has no rows**
   - The app reads from the **sales_master** table (tenant `default_elettro`). If the table is empty, you get zeros and empty charts.
   - **Fix:** Open the **Data** page in the app → upload an Excel/CSV with columns like DATE, INVOICE_NO, CUSTOMER_NAME, AMOUNT, etc. The backend will insert into Supabase. Then refresh the dashboard.

**Quick checks:**
- Open `https://YOUR-RENDER-URL/` in a browser. You should see `{"status":"ok",...}`. If that fails, the backend is down or sleeping (free tier wakes in ~30–60 s).
- Open `https://YOUR-RENDER-URL/api/dashboard/summary` in a browser. You should get JSON (summary, trend, etc.). If you get CORS or 404, fix the URL or CORS in `backend/main.py`.

**Slow loading / “can’t fetch data”:**
- The app uses a **single** dashboard request (`/dashboard/summary`) plus anomalies, with a **50 s** client timeout. If the backend is cold (Render free tier), the first load can take 30–60 s; if it takes longer, you’ll see “Backend is slow or unreachable … Please retry.” Use **Retry** after the backend has woken.
- For faster, reliable loading: use Render paid (always on) or a keep-warm cron (see §7).

---

## 7. Production-grade (demos, MD, team)

To make the app **fast and reliable** for showing to leadership and team:

1. **Avoid cold starts**
   - **Render free tier** spins down after ~15 min inactivity; the first request can take 30–60 s. For demos or daily use, upgrade to **Render paid** (e.g. Starter $7/mo) so the service stays **always on** and responds in &lt;2 s.
   - Optional: use a free cron (e.g. [cron-job.org](https://cron-job.org)) to hit `https://YOUR-RENDER-URL/` every 10–14 min so the free tier does not spin down during work hours.

2. **Use the proxy**
   - Keep `NEXT_PUBLIC_USE_API_PROXY=true` on Vercel (all environments). This avoids CORS and keeps a single, stable way to call the API.

3. **Client cache (already in the app)**
   - API responses are cached in the browser for **90 seconds**. When you switch sections (e.g. Dashboard → Sales → back to Dashboard), the second load uses cache and feels instant. Refresh the page or wait 90 s to get fresh data.

4. **Before a demo**
   - Open the **Render** service URL in a tab once so it’s awake.
   - Open the **Vercel** app; use filters and click through each section once so cache is warm.
   - Then present: navigation and repeat views will be fast.

5. **Monitoring (optional)**
   - In Render: **Metrics** and **Logs** to spot errors or slowness.
   - In Vercel: **Analytics** and **Logs** for frontend and proxy.

---

## 8. Alternate options

If the default setup (Vercel + Render + Supabase) is slow or keeps failing, you have alternatives:

| Option | Pros | Cons |
|--------|------|------|
| **Render paid (Starter ~$7/mo)** | Same stack, no cold starts, faster and more reliable. | Monthly cost. |
| **Different backend host** | Deploy the same FastAPI app on **Railway**, **Fly.io**, or a **VPS** (DigitalOcean, etc.). Often better uptime and control. | Need to point `NEXT_PUBLIC_API_URL` to the new URL and redeploy the frontend. |
| **Run backend locally** | For demos or dev: run the backend on your machine (`cd backend && pip install -r requirements.txt && uvicorn main:app`). Set `NEXT_PUBLIC_API_URL=http://localhost:8000/api` and `NEXT_PUBLIC_USE_API_PROXY=false` in the frontend. | Only works when your laptop is on and the app is running; not for sharing 24/7. |
| **Backendless (Vercel + Supabase only)** | No separate backend service: Next.js API routes or serverless functions call Supabase directly. No Render at all. | Requires rewriting dashboard/analytics/PDF logic from Python (pandas) to TypeScript/Node or a serverless Python runtime; more work. |

**Recommendation:** For a stable demo or production, use **Render paid** or move the backend to **Railway/Fly.io**. For quick local demos, run the backend locally and keep the frontend on Vercel (or run both locally).

---

## 9. Alternate deployment options (full stack)

Alternatives for **each** piece of the stack, so you can mix and match.

### Frontend (instead of Vercel)

| Option | Notes |
|--------|------|
| **Netlify** | Import repo, set **Base directory** = `frontend`, build command `npm run build`, publish `frontend/.next` or use Next.js runtime; add `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_USE_API_PROXY=true`. |
| **Cloudflare Pages** | Next.js supported; set root to `frontend`, env vars as above. |
| **AWS Amplify** | Connect repo, monorepo with root `frontend`; configure env and build. |
| **Self‑host (VPS / Docker)** | Build with `npm run build`, run `npm start` (or use a Dockerfile). Serve behind nginx/Caddy with HTTPS. |
| **Run locally** | `cd frontend && npm run dev`; use with backend on localhost or any deployed backend URL. |

### Backend (instead of Render)

| Option | Notes |
|--------|------|
| **Railway** | New → Deploy from repo; set root to repo root, build `cd backend && pip install -r requirements.txt`, start `uvicorn main:app --host 0.0.0.0` from `backend/`; add `DATABASE_URL`. Point frontend `NEXT_PUBLIC_API_URL` to Railway URL. |
| **Fly.io** | `fly launch` in repo; use a Dockerfile or buildpack. Set `DATABASE_URL` and expose port 8000. |
| **Google Cloud Run** | Containerize backend (Dockerfile), deploy; set env and connect to Cloud SQL or any Postgres. |
| **AWS (ECS / Lambda)** | Run FastAPI in a container or via Mangum for Lambda; more setup. |
| **VPS (DigitalOcean, Linode, etc.)** | SSH in, install Python, run `uvicorn` behind gunicorn + nginx; full control. |
| **Run locally** | `cd backend && pip install -r requirements.txt && uvicorn main:app --port 8000`; set frontend `NEXT_PUBLIC_API_URL=http://localhost:8000/api`. |

### Database (instead of Supabase)

| Option | Notes |
|--------|------|          
| **Neon** | Serverless Postgres; copy connection string, set as `DATABASE_URL` on backend; create/import `sales_master`. |
| **Railway Postgres** | Add Postgres in Railway; use its URL as `DATABASE_URL` if backend is also on Railway. |
| **Supabase Pro** | Same as current; higher egress and limits. |
| **PlanetScale** | MySQL; would require adapter/query changes (app is Postgres-oriented). |
| **Self‑hosted Postgres** | Install Postgres on a VPS or Docker; use connection string with `sslmode` as needed. |

### Egress / cost reduction (Supabase)

- **Longer frontend cache:** In `frontend/src/lib/api.ts`, increase `CACHE_TTL_MS` (e.g. 90 → 300 seconds).
- **EGRESS_MAX_YEARS:** Set to `2` or `3` on the backend env to only load recent years (§4).
- **Supabase Pro:** Higher egress quota.

### Full-stack combos (examples)

- **Vercel + Railway + Neon** — Frontend on Vercel, backend + Postgres on Railway, or Postgres on Neon and backend on Railway.
- **All-in-one VPS** — One server: Nginx → Next.js (frontend) + Gunicorn/Uvicorn (backend) + Postgres; single `DATABASE_URL` and no cold starts.
- **Vercel + Render paid + Supabase** — Default stack with paid Render and (optionally) Supabase Pro for stability and higher limits.

To switch any layer: update **env vars** (e.g. `NEXT_PUBLIC_API_URL` for frontend, `DATABASE_URL` for backend), ensure **sales_master** exists for Postgres, then redeploy. The app uses standard Postgres and HTTP; no provider lock-in.

### Best choice by goal

| Goal | Best stack |
|------|------------|
| **Free, quick demo** | Vercel (frontend) + Render free (backend) + Supabase free. Use keep-warm cron and proxy; expect cold starts. |
| **Stable demo / daily use** | **Vercel + Render paid (Starter)** + Supabase. Always-on backend, no cold starts, minimal config. |
| **Low cost, no egress worry** | Vercel + Railway (backend) + **Neon** (Postgres). Generous free tiers; swap `DATABASE_URL` to Neon. |
| **Full control, one bill** | **Single VPS** (e.g. DigitalOcean Droplet): Nginx + Next.js + FastAPI + Postgres. No cold starts, no per-service limits. |
| **Enterprise / scale later** | Vercel + **Fly.io** or **Cloud Run** (backend) + **Neon** or **Supabase Pro**. Good scaling and observability. |

**TL;DR:** For most teams, **Vercel + Render paid + Supabase** (or **Vercel + Railway + Neon**) is the best balance of simplicity and reliability.

### Under $10/month

| Stack | Approx. cost | Notes |
|-------|--------------|--------|
| **All free** | $0 | Vercel + Render free + Supabase free. Use keep-warm cron; cold starts 30–60 s. |
| **Render Starter only** | ~$7/mo | Vercel (free) + **Render paid** + Supabase free. Backend always on, no cold starts. Stays under $10. |
| **Railway (backend + DB)** | ~$5–10/mo | Vercel (free) + Railway (backend + Postgres). Usage-based; light traffic often under $10. |
| **Single VPS** | ~$5–6/mo | One Droplet (e.g. DigitalOcean $6) or Linode: run frontend (Node), backend (Python), Postgres. Full control. |
| **Vercel + Fly.io + Neon** | ~$0–5/mo | All have free tiers; pay only if you exceed. Fly.io free allowance is small; Neon free tier is generous. |

**Best under $10:** **Vercel (free) + Render Starter (~$7)** + Supabase free. Total ~$7/mo, stable and simple.

---

## 10. Deploy Streamlit (sharing + R&D)

Use this so you can **share** the dashboard with others and **do R&D** in parallel with the main Next.js app. The legacy Streamlit app in **`legacy/`** uses the same FastAPI backend (it calls **`/api/v1/data`** and **`/api/v1/upload_batch`**). Deploy the **backend first** (§1); then deploy Streamlit and set **`API_URL`** to your Render backend URL (e.g. `https://elettro-api-xxxx.onrender.com` — no `/api` suffix).

### Option A — Streamlit Community Cloud (free, shareable)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
2. **New app** → select this repo and branch.
3. **Main file path:** `legacy/app.py`
4. **Advanced settings** → **Requirements file:** `legacy/requirements.txt`
5. **Secrets** (in the app’s Settings or as `.streamlit/secrets.toml` in the repo):  
   - `API_URL` = `https://YOUR-RENDER-URL` (e.g. `https://elettro-api-xxxx.onrender.com`)  
   - `DATABASE_URL` = your Supabase connection string (if the app uses direct DB; otherwise optional)
6. Deploy. Share the generated URL (e.g. `https://your-app.streamlit.app`) with others.

**Note:** If the app fails to start (e.g. missing `config` or paths), ensure the app runs from the **repo root** so `legacy/config.py` and `legacy/analytics` are on the path. On Community Cloud, the working directory is usually the repo root when Main file path is `legacy/app.py`.

### Option B — Render (second web service)

1. In [dashboard.render.com](https://dashboard.render.com): **New** → **Web Service**; connect the same repo.
2. **Root Directory:** leave empty (repo root).
3. **Build Command:** `pip install -r legacy/requirements.txt`
4. **Start Command:** `streamlit run legacy/app.py --server.port=$PORT --server.address=0.0.0.0`
5. **Environment:**  
   - `API_URL` = `https://YOUR-RENDER-BACKEND-URL` (no `/api`)  
   - `DATABASE_URL` = your Supabase URL (if needed)
6. Create the service. Your Streamlit app will have its own URL (e.g. `https://elettro-streamlit-xxxx.onrender.com`). Share that link for R&D or demos.

**Running both in parallel:** Use **Next.js on Vercel** for production and **Streamlit** (Community Cloud or Render) for sharing and experiments. Both hit the same backend and database, so data stays in sync.

---

**More (VPS, Docker, detailed steps):** see **docs/DEPLOYMENT.md**.
