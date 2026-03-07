# Deploy Now — Next.js + FastAPI

Use this after code is pushed to GitHub. You need: **GitHub repo**, **Supabase** `DATABASE_URL`, and accounts on **Render** + **Vercel** (free tiers OK).

---

## 1. Backend on Render

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Web Service**.
2. Connect your GitHub repo (`kn-elettro-industries/sales-dashboard` or your fork).
3. If the repo has a **render.yaml** at root:
   - You can use **New** → **Blueprint** and connect the repo; Render will create the service from `render.yaml`.  
   - Then open the service → **Environment** → add **DATABASE_URL** (your Supabase connection string).
4. If setting up manually:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment:** Add `DATABASE_URL` = Supabase URL (Transaction pooler, with `?sslmode=require`).
5. Click **Create Web Service**. Wait for deploy.
6. Copy the service URL, e.g. `https://elettro-api-xxxx.onrender.com`.

---

## 2. Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project**.
2. Import the same GitHub repo.
3. **Root Directory:** set to `frontend` (Override).
4. **Environment Variables:** Add:
   - Name: `NEXT_PUBLIC_API_URL`  
   - Value: `https://YOUR-RENDER-URL/api`  
   (e.g. `https://elettro-api-xxxx.onrender.com/api` — use the URL from step 1, add `/api`.)
5. Deploy. Copy your frontend URL, e.g. `https://sales-dashboard-xxx.vercel.app`.

---

## 3. CORS (so frontend can call backend)

1. In the repo, open `backend/main.py`.
2. In the `origins` list, add your Vercel URL (and remove `"*"` for production if you want):
   ```python
   origins = [
       "http://localhost:3000",
       "https://dashboard.elettro.in",
       "https://sales-dashboard-xxx.vercel.app",  # your Vercel URL
       "*"   # or remove this and keep only the URLs above
   ]
   ```
3. Commit and push. Render will auto-redeploy the backend.

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

**More options (VPS, Docker):** see **docs/DEPLOYMENT.md**.
