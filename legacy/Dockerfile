# Build from repo root: docker build -f legacy/Dockerfile .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATA_DIR=/app/data

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

COPY legacy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY legacy/ .
COPY assets/ /app/assets/
COPY shared/ /app/shared/

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || true
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
