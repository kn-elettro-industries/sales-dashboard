#!/bin/sh
# Ensures PORT is set (Render sets it; this defaults to 8000 if missing)
port="${PORT:-8000}"
echo "Starting uvicorn on 0.0.0.0:$port"
exec uvicorn main:app --host 0.0.0.0 --port "$port"
