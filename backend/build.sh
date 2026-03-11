#!/usr/bin/env bash
# Render build script for backend
# Ensures fpdf2 is the ONLY fpdf library installed (PyFPDF shares the same
# module namespace and causes blank PDFs when it wins the import race)

set -o errexit

echo "=== Installing Python dependencies ==="
pip install -r requirements.txt

echo "=== Removing old PyFPDF if present (conflicts with fpdf2) ==="
pip uninstall -y fpdf || true   # old PyFPDF package name

echo "=== Verifying fpdf2 is installed ==="
python -c "import fpdf; print('fpdf version:', fpdf.__version__)"

echo "=== Build complete ==="
