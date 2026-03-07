# Making the ELETTRO Sales Pipeline Platform Live

*(This file lives in `docs/`. See repo root `STRUCTURE.md` for folder layout.)*

This guide covers how to deploy the **frontend** (Next.js) and **backend** (FastAPI) so the platform is accessible on the internet.

---

## Architecture

| Part      | Tech        | Purpose                    |
|-----------|-------------|----------------------------|
| Frontend  | Next.js 16  | Dashboard UI               |
| Backend   | FastAPI     | API, reports, chatbot, DB  |
| Database  | PostgreSQL  | Supabase (or your Postgres)|

The frontend calls the backend using `NEXT_PUBLIC_API_URL`. The backend uses `DATABASE_URL` for PostgreSQL (Supabase by default).

---

## Option A: Easiest — Vercel (frontend) + Render (backend)

### 1. Backend on Render

1. Push your repo to **GitHub** (or GitLab).
2. Go to [render.com](https://render.com) → **New** → **Web Service**.
3. Connect the repo and set:
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. In **Environment** add:
   - `DATABASE_URL` = your Supabase connection string (or Postgres URL).  
     Example: `postgresql://...@...supabase.com:6543/postgres?sslmode=require`
5. Deploy. Note the backend URL, e.g. `https://your-api.onrender.com`.

### 2. Frontend on Vercel

1. Go to [vercel.com](https://vercel.com) → **Add New** → **Project** → import your repo.
2. Set:
   - **Root Directory:** `frontend`
   - **Framework:** Next.js (auto-detected)
3. In **Environment Variables** add:
   - `NEXT_PUBLIC_API_URL` = `https://your-api.onrender.com/api`  
     (no trailing slash if your code appends paths like `/api/...`; your code uses `/api` as prefix, so use `https://your-api.onrender.com` and the app will call `.../api/...` — check `frontend/src/lib/api.ts`: if it already appends `/api`, set `NEXT_PUBLIC_API_URL=https://your-api.onrender.com`; if it does not, set `https://your-api.onrender.com/api`. Your api.ts uses `API_BASE_URL` and then paths like `/stats/dashboard` so the backend serves at `/api`, so base URL should be `https://your-api.onrender.com` and paths in code are like `/api/stats/dashboard` — so **NEXT_PUBLIC_API_URL = `https://your-api.onrender.com/api`**.)
4. Deploy. You’ll get a URL like `https://your-app.vercel.app`.

### 3. CORS

In `backend/main.py`, `origins` already includes `"*"` and `https://dashboard.elettro.in`. For your Vercel app, add your Vercel URL:

```python
origins = [
    "http://localhost:3000",
    "https://dashboard.elettro.in",
    "https://your-app.vercel.app",  # your Vercel URL
    "*"  # or remove "*" in production and list only your frontend URLs
]
```

Redeploy the backend after changing CORS.

### 4. Database (Supabase)

- You already use **Supabase** PostgreSQL in `backend/api/db.py` via `DATABASE_URL`.
- In production, set `DATABASE_URL` on Render to your Supabase project’s connection string (Project Settings → Database → Connection string, use “Transaction” pooler and `?sslmode=require`).
- Ensure the `sales_master` table (and schema) exist; the app expects this table and `tenant_id`.

---

## Option B: Single VPS (e.g. Ubuntu)

Good if you want one server for both frontend and backend.

### 1. Server

- Create an Ubuntu 22.04 VPS (DigitalOcean, AWS, etc.).
- SSH in and install: Node 20+, Python 3.11+, and (optional) Nginx.

### 2. Backend

```bash
cd /opt
sudo git clone <your-repo-url> sales_pipeline
cd sales_pipeline/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `/etc/systemd/system/elettro-api.service`:

```ini
[Unit]
Description=ELETTRO FastAPI Backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/sales_pipeline/backend
Environment="DATABASE_URL=postgresql://..."
Environment="PORT=8000"
ExecStart=/opt/sales_pipeline/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable elettro-api
sudo systemctl start elettro-api
```

### 3. Frontend

```bash
cd /opt/sales_pipeline/frontend
npm ci
echo "NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000/api" > .env.production.local
npm run build
npm run start
```

Or run under PM2:

```bash
npm install -g pm2
pm2 start npm --name "elettro-frontend" -- start
pm2 save && pm2 startup
```

### 4. Nginx (optional, for HTTPS and one domain)

- Point a domain (e.g. `dashboard.elettro.in`) to the VPS.
- Install certbot and Nginx, then proxy:
  - `https://dashboard.elettro.in` → `http://127.0.0.1:3000`
  - `https://api.elettro.in` (or `/api` on same domain) → `http://127.0.0.1:8000`

Then set `NEXT_PUBLIC_API_URL` to `https://api.elettro.in/api` (or your chosen API URL).

---

## Option C: Docker (from repo root)

A **backend-only** Dockerfile is provided that builds from the repo root so the backend runs in a container (e.g. on Railway, Fly.io, or your own Docker host).

### Build and run backend

From the **repository root**:

```bash
docker build -f backend/Dockerfile -t elettro-backend .
docker run -p 8000:8000 -e DATABASE_URL="postgresql://..." elettro-backend
```

Then run the frontend locally or deploy it to Vercel with `NEXT_PUBLIC_API_URL` pointing to the backend (e.g. `http://your-server:8000/api` or your public URL).

---

## Environment variables summary

| Where     | Variable               | Example / purpose                          |
|-----------|------------------------|--------------------------------------------|
| Backend   | `DATABASE_URL`         | Supabase/Postgres URL with `?sslmode=require` |
| Backend   | `PORT`                 | Optional; Render/VPS set this (e.g. 8000)  |
| Frontend  | `NEXT_PUBLIC_API_URL`  | Backend base URL including `/api`, e.g. `https://your-api.onrender.com/api` |

---

## After going live

1. **Restrict CORS** in `backend/main.py`: remove `"*"` and list only your frontend origin(s).
2. **Secrets:** Never commit real `DATABASE_URL` or API keys; use env vars on the host (Vercel, Render, or VPS).
3. **HTTPS:** Use HTTPS for both frontend and backend in production (Vercel and Render provide it; on VPS use Nginx + Certbot).
4. **Health check:** Backend root `GET /` returns `{"status":"ok"}`; use it for uptime checks.

If you tell me your chosen option (e.g. “Vercel + Render” or “single VPS”), I can give you exact commands and a minimal CORS snippet for your URLs.
