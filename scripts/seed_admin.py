"""
Create user accounts. Only admin can run this — signup is disabled by default.

Usage:
  python scripts/seed_admin.py                  # Create default admin (admin/admin123)
  python scripts/seed_admin.py add <user> <pw> # Create a new user (you choose credentials)
"""
import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_backend = os.path.join(_root, "backend")
os.chdir(_backend)
sys.path.insert(0, _backend)


def add_user(username: str, password: str, role: str = "viewer") -> bool:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, ".env"))
    load_dotenv(os.path.join(_backend, ".env"))

    from api.db import create_user

    if not os.environ.get("DATABASE_URL"):
        print("ERROR: DATABASE_URL is not set. Set it in .env or environment.")
        return False

    err = create_user(username, password, role=role)
    if err is None:
        print(f"Created user: {username}")
        return True
    elif "already taken" in err.lower():
        print(f"User '{username}' already exists.")
        return True
    else:
        print(f"Failed: {err}")
        return False


def main():
    args = sys.argv[1:]
    if args and args[0].lower() == "add":
        if len(args) != 3:
            print("Usage: python scripts/seed_admin.py add <username> <password>")
            sys.exit(1)
        _, username, password = args
        ok = add_user(username, password)
        sys.exit(0 if ok else 1)

    # Default: seed admin
    ok = add_user("admin", "admin123", role="admin")
    if ok:
        print("  Username: admin")
        print("  Password: admin123")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
