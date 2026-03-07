# Deploy Frontend to Vercel

Use this to deploy the **Next.js** dashboard (frontend only). The backend must already be deployed (e.g. on Render) and reachable via HTTPS.

---

## 1. Connect the repo

1. Go to [vercel.com](https://vercel.com) and sign in (GitHub).
2. Click **Add New** → **Project**.
3. Import **kn-elettro-industries/sales-dashboard** (or your fork).
4. Click **Import**.

---

## 2. Configure the project

| Setting | Value |
|--------|--------|
| **Framework Preset** | Next.js (auto-detected) |
| **Root Directory** | `frontend` ← **Set this.** Click "Edit" and enter `frontend`. |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | (leave default) |
| **Install Command** | `npm install` (default) |

---

## 3. Environment variable

Add one variable so the app talks to your backend:

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_API_URL` | `https://YOUR-RENDER-URL/api` |

Examples:

- `https://elettro-api-xxxx.onrender.com/api`
- `https://sales-dashboard-wfay.onrender.com/api`

Use your **actual** Render (or backend) URL and add `/api` at the end. No trailing slash after `api`.

---

## 4. Deploy

Click **Deploy**. Wait for the build to finish.

Your dashboard will be at: `https://your-project-xxx.vercel.app`.

---

## 5. After deploy

- **CORS:** In your backend (e.g. `backend/main.py`), add your Vercel URL to the `origins` list so the API accepts requests from the frontend.
- **Custom domain:** In Vercel → Project → Settings → Domains you can add e.g. `dashboard.elettro.in`.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Failed to fetch" in browser | Check `NEXT_PUBLIC_API_URL` is set and ends with `/api`. Check backend CORS includes your Vercel URL. |
| Build fails: "Cannot find module" | Ensure **Root Directory** is `frontend`. |
| 404 on refresh | Next.js + Vercel handle this by default; if using custom server or rewrites, check `next.config` / `vercel.json`. |
