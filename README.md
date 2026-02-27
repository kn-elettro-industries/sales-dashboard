# K.N. Elettro — Sales Intelligence Platform

A cloud-deployed sales analytics platform built for Indian manufacturers. Upload invoices, get instant dashboards with GST breakdowns, customer analytics, and revenue forecasting.

## Live URLs

| Service | URL |
|---|---|
| **Dashboard** | [elettro-dashboard.onrender.com](https://elettro-dashboard.onrender.com) |
| **API** | [sales-dashboard-wfay.onrender.com](https://sales-dashboard-wfay.onrender.com) |

## Architecture

```
Browser (Anywhere)
    ↓
Render: Streamlit Dashboard  ←→  Render: FastAPI API
                                        ↓
                               Supabase (PostgreSQL)
```

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| Database | Supabase (PostgreSQL) |
| ETL | Pandas + Custom Pipeline |
| Analytics | Prophet, Scikit-learn, Plotly |
| Hosting | Render.com (Free Tier) |

## Project Structure

```
├── app.py                    # Streamlit dashboard (main entry)
├── config.py                 # Configuration & environment vars
├── database.py               # SQLAlchemy + Supabase connection
├── auth.py                   # User authentication
├── etl_pipeline.py           # Extract, Transform, Load pipeline
├── pipeline_monitor.py       # Pipeline status tracking
├── cloud_data_wrapper.py     # Cloud file upload widget
├── watcher.py                # Local file watcher (dev mode)
├── requirements.txt          # Python dependencies
├── Dockerfile                # Frontend container
├── docker-compose.yml        # Local dev with Docker
│
├── analytics/                # Analytics & visualization modules
│   ├── kpi.py                # Key Performance Indicators
│   ├── reporting.py          # Charts & report generation
│   ├── forecasting.py        # Revenue forecasting (Prophet)
│   ├── segmentation.py       # Customer segmentation
│   ├── chatbot.py            # AI assistant (Krishiv)
│   └── theme.py              # ELETTRO brand theme
│
├── backend/                  # FastAPI REST API
│   ├── main.py               # API endpoints (health, data, upload)
│   └── Dockerfile            # Backend container
│
├── data/                     # Data files (gitignored)
│   ├── raw/                  # Original Excel uploads
│   ├── masters/              # Customer master, targets
│   ├── output/               # Processed outputs
│   └── processed/            # Archive
│
├── scripts/                  # Utility & setup scripts
├── reports/                  # Report templates
├── assets/                   # Logo & brand assets
└── tests/                    # Test files
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run Streamlit
streamlit run app.py

# Run FastAPI
cd backend && uvicorn main:app --reload
```

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `API_URL` | FastAPI backend URL |

## License

Proprietary — K.N. Elettro Industries
