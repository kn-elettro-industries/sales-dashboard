# Deploy tomorrow – quick checklist

*(In `docs/`. Deployment uses `frontend/` and `backend/` from repo root.)*

Use this when you’re ready to go live (cheapest no-sleep: ~$7/mo on Render only).

---

## Deploy without affecting the old repo

If your **old** app is already on GitHub (e.g. `kn-elettro-industries/sales-dashboard` or `Commanderadi/sales-dashboard`), use one of these so the old deployment keeps working:

### Option A: New GitHub repo (safest – old repo untouched)

1. Create a **new** repository on GitHub (e.g. `sales-pipeline-v2` or `elettro-dashboard-next`).
2. In this project folder, add it as a remote and push:
   ```bash
   git remote add new-repo https://github.com/YOUR_ORG/sales-pipeline-v2.git
   git push -u new-repo main
   ```
3. In **Render** and **Vercel**, connect the **new** repo (not the old one). Use Root Directory `backend` / `frontend` as below. Your old repo and its deployments are never touched.

### Option B: Same repo, new branch (one repo, two deployments)

1. Push this code to a **new branch** (do **not** force-push to `main`):
   ```bash
   git checkout -b next
   git add .
   git commit -m "New Next.js + FastAPI stack"
   git push -u origin next
   ```
2. In **Render**: create a **new** Web Service, connect the **same** repo, but set **Branch** to `next` (not `main`). Root Directory: `backend`.
3. In **Vercel**: create a **new** Project, import the same repo, set **Branch** to `next`. Root Directory: `frontend`.
4. Your existing (old) Render/Vercel apps keep using `main`; the new apps use `next`. No conflict.

---

## Before you start

- [ ] Code pushed to **GitHub** (new repo or new branch – see above)
- [ ] **Supabase** project has `sales_master` table and you have the **connection string** (Settings → Database → Connection string, use “Transaction” pooler, add `?sslmode=require`)

---

## 1. Backend on Render (~$7/mo – no sleep)

- [ ] Go to [render.com](https://render.com) → **New** → **Web Service**
- [ ] Connect your repo
- [ ] Set **Root Directory:** `backend`
- [ ] **Build:** `pip install -r requirements.txt`
- [ ] **Start:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] Add env var: `DATABASE_URL` = your Supabase connection string
- [ ] Deploy and copy your backend URL, e.g. `https://your-app.onrender.com`

---

## 2. Frontend on Vercel (free)

- [ ] Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import same repo
- [ ] Set **Root Directory:** `frontend`
- [ ] Add env var: `NEXT_PUBLIC_API_URL` = `https://your-app.onrender.com/api` (your real Render URL + `/api`)
- [ ] Deploy

---

## 3. CORS

- [ ] In `backend/main.py`, add your Vercel URL to the `origins` list (e.g. `https://your-app.vercel.app`) and remove `"*"` for production
- [ ] Commit, push; Render will auto-redeploy

---

## 4. Test

- [ ] Open your Vercel URL and check dashboard loads
- [ ] Try filters, reports, chatbot – all should hit the Render backend

---

**Full details:** see **docs/DEPLOYMENT.md**.
