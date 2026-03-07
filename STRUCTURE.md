# Project structure

High-level layout of the repo after restructuring.

```
sales_pipeline/
├── frontend/           # Next.js dashboard (current UI)
│   ├── src/
│   │   ├── app/        # Pages (dashboard, sales, reports, …)
│   │   ├── components/
│   │   └── lib/        # API client
│   └── package.json
│
├── backend/            # FastAPI API (current backend)
│   ├── main.py
│   ├── api/
│   │   ├── routes.py
│   │   ├── db.py
│   │   ├── chatbot.py
│   │   └── pdf_generator.py
│   ├── requirements.txt
│   └── Dockerfile      # Build from repo root: docker build -f backend/Dockerfile .
│
├── legacy/             # Old Streamlit app (optional local use)
│   ├── app.py          # Streamlit entry
│   ├── config.py, database.py, etl_pipeline.py, …
│   ├── analytics/      # Modules used by Streamlit app
│   ├── requirements.txt
│   └── Dockerfile      # Build from repo root: docker build -f legacy/Dockerfile .
│
├── docs/               # All documentation
│   ├── DEPLOYMENT.md
│   ├── DEPLOY-TOMORROW.md
│   ├── VISION.md, PROJECT_JOURNEY.md, …
│   ├── ELETTRO_Platform_Documentation.pdf
│   └── engineering_journal/
│
├── assets/             # Logos, CSS (used by backend PDF + legacy app)
├── data/               # Local data (masters, raw, output)
├── scripts/            # Utility scripts and .bat helpers
├── tests/
├── reports/
│
├── docker-compose.yml  # Postgres (optional local)
├── README.md
└── STRUCTURE.md        # This file
```

## What to use when

| Goal | Use |
|------|-----|
| **Deploy / run the live platform** | `frontend/` + `backend/` (see `docs/DEPLOYMENT.md`) |
| **Run legacy Streamlit app locally** | `cd legacy` then `streamlit run app.py` (data/ and assets/ at repo root) |
| **Docs and deployment steps** | `docs/` |

## Paths

- **Data:** `data/` at repo root (masters, raw, output). Legacy app uses it via `config.py` (BASE_DIR = repo root).
- **Assets:** `assets/` at repo root. Backend (e.g. PDF) and legacy app both use it.
- **Documentation:** Everything is under `docs/` (including `DEPLOYMENT.md` and `DEPLOY-TOMORROW.md`).
