#!/bin/sh
# Run from repo root so backend is found. Use when Render (or similar) runs from root.
cd "$(dirname "$0")/backend" || exit 1
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
