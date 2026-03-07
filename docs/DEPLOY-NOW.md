# Deploy Now — Next.js + FastAPI

Use this after code is pushed to GitHub. You need: **GitHub repo**, **Supabase** `DATABASE_URL`, and accounts on **Render** + **Vercel** (free tiers OK).

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
   - **To avoid CORS issues:** set `NEXT_PUBLIC_USE_API_PROXY` = `true`. The app will call your own `/api/proxy`, which forwards to the Render backend server-side (no cross-origin requests from the browser).
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

---

**More options (VPS, Docker):** see **docs/DEPLOYMENT.md**.
