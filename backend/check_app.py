#!/usr/bin/env python3
"""Run before uvicorn to verify app import. Prints any traceback to stdout so Render logs show it."""
import sys
import traceback

if __name__ == "__main__":
    try:
        import main as _main
        print("App import OK", flush=True)
        sys.exit(0)
    except Exception as e:
        print("App import FAILED:", file=sys.stdout)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        sys.stderr.flush()
        sys.exit(1)
