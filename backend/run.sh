#!/bin/sh
# Run from repo root as: sh backend/run.sh  OR  from backend as: sh run.sh
cd "$(dirname "$0")" || exit 1
port="${PORT:-8000}"
echo "Testing app import..."
python check_app.py || exit 1
echo "Starting uvicorn on 0.0.0.0:$port"
exec uvicorn main:app --host 0.0.0.0 --port "$port"
