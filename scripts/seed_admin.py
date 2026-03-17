"""
Seed a default admin user for local development.
Run from repo root: python scripts/seed_admin.py

Default credentials:
  Username: admin
  Password: admin123
"""
import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_backend = os.path.join(_root, "backend")
os.chdir(_backend)
sys.path.insert(0, _backend)

def main():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, ".env"))
    load_dotenv(os.path.join(_backend, ".env"))

    from api.db import create_user

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL is not set. Set it in .env or environment.")
        sys.exit(1)

    err = create_user("admin", "admin123", role="admin")
    if err is None:
        print("Created default admin user.")
        print("  Username: admin")
        print("  Password: admin123")
    elif "already taken" in err.lower():
        print("Admin user already exists.")
        print("  Username: admin")
        print("  Password: admin123")
    else:
        print(f"Failed: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
