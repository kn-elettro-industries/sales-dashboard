#!/usr/bin/env python3
"""
Generate Platform Technical Documentation PDF.
Run from repo root: python scripts/generate_platform_doc_pdf.py
Requires: pip install fpdf2 (or use backend venv)
Output: docs/Platform_Technical_Documentation.pdf
"""
import os
import sys
from pathlib import Path

try:
    import fpdf
    if not getattr(fpdf, "__version__", "0").startswith("2"):
        raise ImportError("fpdf2 2.x required")
    from fpdf import FPDF
except ImportError:
    print("Run: pip install fpdf2")
    sys.exit(1)


def sanitize(s):
    """FPDF is latin-1 based; avoid unicode issues."""
    s = "" if s is None else str(s)
    return s.encode("latin-1", errors="replace").decode("latin-1")


class DocPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.repeat_table_header = False

    def header(self):
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 6, "K.N. Elettro Sales Pipeline - Platform Technical Documentation", 0, 1, "R")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", 0, 0, "C")

    def section_title(self, title):
        self.add_page()
        self.set_font("Arial", "B", 14)
        self.set_fill_color(33, 37, 41)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, sanitize(title), 0, 1, "L", 1)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def subsection(self, title):
        self.set_font("Arial", "B", 11)
        self.cell(0, 7, sanitize(title), 0, 1)
        self.set_font("Arial", "", 9)
        self.ln(2)

    def body(self, text):
        self.set_font("Arial", "", 9)
        self.set_x(self.l_margin)  # Ensure left margin
        self.multi_cell(190, 6, sanitize(text))

    def table_row(self, cells, header=False):
        w = 190.0 / len(cells)
        for i, c in enumerate(cells):
            if header:
                self.set_font("Arial", "B", 8)
                self.set_fill_color(60, 60, 60)
                self.set_text_color(255, 255, 255)
            self.cell(w, 6, sanitize(str(c))[:50], 0, 0, "L", header)
            if header:
                self.set_text_color(0, 0, 0)
                self.set_font("Arial", "", 8)
        self.ln()

    def bullet_items(self, items):
        for item in items:
            self.set_font("Arial", "", 9)
            self.cell(5)
            self.cell(0, 6, "- " + sanitize(str(item)), 0, 1)


def main():
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    pdf = DocPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 22)
    pdf.set_fill_color(33, 37, 41)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "K.N. Elettro", 0, 1, "L", 1)
    pdf.set_font("Arial", "B", 18)
    pdf.cell(0, 12, "Sales Pipeline - Platform Technical Documentation", 0, 1, "L", 1)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 10)
    pdf.ln(8)
    pdf.multi_cell(0, 6, sanitize(
        "This document provides a comprehensive technical overview of the Sales Intelligence Platform: "
        "folder structure, API endpoints, frontend pages, data flow, configuration, and deployment."
    ))
    pdf.ln(4)
    pdf.set_font("Arial", "I", 9)
    pdf.cell(0, 6, "Generated: Platform Documentation", 0, 1)

    # --- 1. Repo Structure ---
    pdf.section_title("1. Repository Folder Structure")

    pdf.subsection("Root")
    pdf.table_row(["Path", "Purpose"], header=True)
    for row in [
        ["README.md", "Project overview, stack, dev, live URLs"],
        ["STRUCTURE.md", "Layout and path conventions"],
        [".gitignore", "Excludes data, env, build artifacts"],
        ["render.yaml", "Render Blueprint for backend"],
        ["docker-compose.yml", "Local Postgres (optional)"],
        ["start-backend.sh", "Starts backend for Render"],
    ]:
        pdf.table_row(row)

    pdf.subsection("frontend/ - Next.js Dashboard")
    pdf.table_row(["Path", "Purpose"], header=True)
    for row in [
        ["src/app/layout.tsx", "Root layout, providers, sidebar"],
        ["src/app/page.tsx", "Executive Summary"],
        ["src/app/sales/page.tsx", "Sales & Growth"],
        ["src/app/customers/page.tsx", "Customer Intelligence"],
        ["src/app/materials/page.tsx", "Material Performance"],
        ["src/app/geographic/page.tsx", "Geographic Intelligence"],
        ["src/app/risk/page.tsx", "Risk Management"],
        ["src/app/data/page.tsx", "Cloud Data Uploader"],
        ["src/app/reports/page.tsx", "Industrial Reporting"],
        ["src/components/ui/", "Sidebar, Charts, DataTable, IndiaMap, ChatWidget"],
        ["src/lib/api.ts", "API client, cache"],
        ["public/", "logo, india-states.geojson"],
    ]:
        pdf.table_row(row)

    pdf.subsection("backend/ - FastAPI API")
    pdf.table_row(["Path", "Purpose"], header=True)
    for row in [
        ["main.py", "FastAPI app, CORS, middleware"],
        ["api/routes.py", "All API routes"],
        ["api/db.py", "DB engine, get_tenant_data"],
        ["api/chatbot.py", "NLP query engine"],
        ["api/pdf_generator.py", "PDF reports"],
        ["requirements.txt", "Dependencies"],
        ["Dockerfile", "Build from repo root"],
    ]:
        pdf.table_row(row)

    pdf.subsection("legacy/ - Streamlit App")
    pdf.table_row(["Path", "Purpose"], header=True)
    for row in [
        ["app.py", "Streamlit entry, auth, menus"],
        ["config.py", "Paths, DATABASE_URL, API_URL"],
        ["database.py", "DB access"],
        ["etl_pipeline.py", "Standardize, taxes, merge"],
        ["auth.py", "JSON auth, roles"],
        ["analytics/", "kpi, forecasting, risk, reporting, chatbot..."],
        ["Dockerfile", "Streamlit port 8501"],
    ]:
        pdf.table_row(row)

    pdf.subsection("shared/ - Shared Python")
    pdf.table_row(["Path", "Purpose"], header=True)
    pdf.table_row(["geo_data.py", "CITY_COORDS, STATE_COORDS for maps"])
    pdf.table_row(["__init__.py", "Package init"])

    pdf.subsection("scripts/, data/, assets/, docs/, tests/")
    pdf.body("scripts/: regenerate_excel, check_db, Run_App.bat, Start_Backend.bat, etc.")
    pdf.body("data/: raw, masters, output, processed (gitignored)")
    pdf.body("assets/: style.css, logos (backend PDF, legacy)")
    pdf.body("docs/: DEPLOYMENT.md, VISION.md, engineering_journal/")
    pdf.body("tests/: test_etl.py (ETL unit tests)")

    # --- 2. Backend API ---
    pdf.section_title("2. Backend API Endpoints")

    pdf.subsection("Auth")
    pdf.table_row(["Method", "Endpoint", "Purpose"], header=True)
    for row in [
        ["POST", "/api/auth/login", "Mock login"],
        ["GET", "/api/auth/me", "Current user"],
    ]:
        pdf.table_row(row)

    pdf.subsection("Data & Upload")
    for row in [
        ["POST", "/api/data/clear", "Clear tenant data"],
        ["POST", "/api/upload/customer-master", "Customer master upload"],
        ["POST", "/api/upload", "Sales file upload (xlsx/csv)"],
        ["GET", "/api/v1/data", "Full tenant data"],
        ["POST", "/api/v1/upload_batch", "Batch upload"],
        ["GET", "/api/data/health", "Data quality metrics"],
    ]:
        pdf.table_row(row)

    pdf.subsection("Reports")
    for row in [
        ["GET", "/api/reports/test-pdf", "Test PDF"],
        ["GET", "/api/reports/download", "Executive/Distributor PDF"],
        ["POST", "/api/reports/dynamic", "Custom dynamic report"],
    ]:
        pdf.table_row(row)

    pdf.subsection("Analytics & Dashboard")
    for row in [
        ["GET", "/api/dashboard/summary", "Summary, trend, materials, top customers"],
        ["GET", "/api/metrics/summary", "KPI summary"],
        ["GET", "/api/charts/trend", "Trend chart"],
        ["GET", "/api/sales/monthly", "Monthly sales"],
        ["GET", "/api/sales/growth", "Growth metrics"],
        ["GET", "/api/customers/all", "All customers"],
        ["GET", "/api/customers/rfm", "RFM segments"],
        ["GET", "/api/geographic/states", "State-level data"],
        ["GET", "/api/geographic/cities", "City-level data"],
        ["GET", "/api/materials/performance", "Material performance"],
        ["GET", "/api/analytics/anomalies", "Revenue anomalies"],
    ]:
        pdf.table_row(row)

    pdf.subsection("Other")
    for row in [
        ["GET", "/api/filters/options", "Filter options"],
        ["POST", "/api/chat", "Chatbot query"],
        ["GET", "/api/export/data", "Export data"],
    ]:
        pdf.table_row(row)

    pdf.body("Common query params: tenant_id, start_date, end_date, states, cities, customers, material_groups")

    # --- 3. Frontend ---
    pdf.section_title("3. Frontend App Structure")

    pdf.subsection("Pages (App Router)")
    pdf.table_row(["Route", "Page", "Purpose"], header=True)
    for row in [
        ["/", "Executive Summary", "KPIs, trend, materials, top customers"],
        ["/sales", "Sales & Growth", "Monthly/daily charts, growth"],
        ["/customers", "Customer Intelligence", "RFM, table"],
        ["/materials", "Material Performance", "Pareto, charts"],
        ["/geographic", "Geographic Intelligence", "India map, state/city"],
        ["/risk", "Risk Management", "Risk metrics"],
        ["/data", "Cloud Data Uploader", "File drop, upload"],
        ["/reports", "Industrial Reporting", "Report generation, PDFs"],
    ]:
        pdf.table_row(row)

    pdf.subsection("Key Components")
    pdf.bullet_items([
        "Sidebar, GlobalFilterBar, OnboardingBanner",
        "DataTable, KpiCard, IndiaMap",
        "Charts (Area, Donut, Bar)",
        "FilterProvider, AuthProvider",
        "ChatWidget, ClientKeyboardShortcuts",
    ])

    # --- 4. Data Flow ---
    pdf.section_title("4. Data Flow & Configuration")

    pdf.subsection("Data Flow")
    pdf.body(
        "Excel/CSV Upload (frontend or legacy) -> FastAPI /upload or /v1/upload_batch -> "
        "ETL: standardize, coalesce_state, material mappings, exclusions, taxes -> "
        "update_database() -> PostgreSQL sales_master -> get_tenant_data() (4h TTL) -> "
        "API endpoints -> JSON -> Frontend"
    )

    pdf.subsection("Database")
    pdf.body("Table: sales_master (multi-tenant via tenant_id). Key columns: DATE, AMOUNT, INVOICE_NO, CUSTOMER_NAME, STATE, CITY, FINANCIAL_YEAR, MONTH, material group.")

    pdf.subsection("Environment Variables")
    pdf.table_row(["Variable", "Where", "Purpose"], header=True)
    for row in [
        ["DATABASE_URL", "Backend, Legacy", "Postgres/Supabase"],
        ["API_URL", "Legacy", "FastAPI base (e.g. localhost:8000)"],
        ["NEXT_PUBLIC_API_URL", "Frontend", "API base including /api"],
        ["NEXT_PUBLIC_USE_API_PROXY", "Frontend", "Use proxy vs direct API"],
        ["PORT", "Backend", "Server port"],
        ["DATA_DIR", "Legacy", "Override data dir (Docker)"],
    ]:
        pdf.table_row(row)

    # --- 5. Deployment ---
    pdf.section_title("5. Deployment")

    pdf.subsection("Current Live")
    pdf.table_row(["Service", "URL/Host"], header=True)
    pdf.table_row(["Dashboard", "elettro-dashboard.onrender.com (Vercel/Render)"])
    pdf.table_row(["API", "sales-dashboard-wfay.onrender.com (Render)"])
    pdf.table_row(["DB", "Supabase PostgreSQL"])

    pdf.subsection("Render (Backend)")
    pdf.body("Blueprint: render.yaml. Build: cd backend, pip install. Start: start-backend.sh or uvicorn main:app.")

    pdf.subsection("Vercel (Frontend)")
    pdf.body("Root: frontend. Build: npm run build. Env: NEXT_PUBLIC_API_URL.")

    pdf.subsection("Docker")
    pdf.body("Backend: docker build -f backend/Dockerfile . (from repo root)")
    pdf.body("Legacy: docker build -f legacy/Dockerfile . (Streamlit on 8501)")

    pdf.subsection("Quick Reference")
    pdf.table_row(["Item", "Value"], header=True)
    for row in [
        ["Frontend port", "3000"],
        ["Backend port", "8000"],
        ["Legacy port", "8501"],
        ["Default tenant", "default_elettro"],
        ["API prefix", "/api"],
    ]:
        pdf.table_row(row)

    # --- 6. Recent Reorganization (2026-03-11) ---
    pdf.section_title("6. Folder Reorganization (2026-03-11)")

    pdf.subsection("Changes")
    pdf.bullet_items([
        "Created shared/ - moved geo_data.py from assets/",
        "Updated imports: assets.geo_data -> shared.geo_data",
        "Fixed test imports: from legacy.etl_pipeline",
        "Added legacy/__init__.py, shared/__init__.py",
        "Fixed README deploy link to DEPLOYMENT.md",
        "Renamed start_backend.bat -> Start_Backend.bat",
        "Updated Dockerfiles to COPY shared/",
    ])

    # Save
    out_path = repo_root / "docs" / "Platform_Technical_Documentation.pdf"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
