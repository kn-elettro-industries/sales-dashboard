import os

# Repo root (parent of legacy/), so data/ and assets/ stay at repo root
_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR = _BASE
# For Cloud Deployments with persistent storage, we read the DATA_DIR env variable
# If not set (like local dev), we use the repo-root "data" folder.
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))

# Folder Paths
RAW_FOLDER = os.path.join(DATA_DIR, "raw")
MASTER_FOLDER = os.path.join(DATA_DIR, "masters")
OUTPUT_FOLDER = os.path.join(DATA_DIR, "output")
PROCESSED_FOLDER = os.path.join(DATA_DIR, "processed")

# Ensure directories exist
for folder in [RAW_FOLDER, MASTER_FOLDER, OUTPUT_FOLDER, PROCESSED_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Database Connection (Supabase Cloud PostgreSQL via psycopg2)
# Note: Using IPv4 Transaction Pooler Host for Windows routing compatibility.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# FastAPI Backend URL
API_URL = os.environ.get("API_URL", "http://localhost:8000")

# Files
CUSTOMER_MASTER_FILE = os.path.join(MASTER_FOLDER, "customer_master.xlsx")
TARGETS_FILE = os.path.join(MASTER_FOLDER, "targets.xlsx")
SALES_MASTER_FILE = os.path.join(OUTPUT_FOLDER, "sales_master.xlsx")
AUDIT_LOG_FILE = os.path.join(OUTPUT_FOLDER, "audit_log.xlsx")
MONTHLY_SUMMARY_FILE = os.path.join(OUTPUT_FOLDER, "monthly_summary.xlsx")

# Business Logic
FY_START_MONTH = 4

# Exclusion List (Material Groups to Ignore) - keyword match: row excluded if MATERIALGROUP contains any of these.
# Keep in sync with backend/api/routes.py EXCLUDED_MATERIAL_GROUPS (exact names there).
EXCLUDE_KEYWORDS = [
    "SERVICE", "AIR VENT", "PACKING", "RAW", "BRASS", "PANEL",
    "SALES ACCOUNT", "MASTER BATCH", "SEMI", "PPCP", "FIXED",
    "PROTECTION", "HIPS", "ABS", "INDIRECT", "NYLOAN", "PP BLACK",
    "NASER MILES PARIS", "DOCUMENT HOLDER",
    "SWISS MILITARY MODLE MAZE",
    "SELF ADHESIVE TIE MOUNT", "SCREW TYPE TIE MOUNT",
    "FINISHED GOOD",  # Finished goods
]

# Rename Mappings (Standardizing Material Groups)
MATERIAL_GROUP_MAPPINGS = {
    r"CONDUIT.*GLAND": "POLYAMIDE CONDUIT GLAND",
    r"REVER": "REVERSE FORWARD",
    r"REVERSE FORWORD": "REVERSE FORWARD"
}
