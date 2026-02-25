# Use official slim Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Make sure default data directory points to a mountable location
ENV DATA_DIR=/app/data

# Set working directory
WORKDIR /app

# Install system dependencies (required for FPDF, pandas, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port 8501 for Streamlit
EXPOSE 8501

# Healthcheck to ensure container is running correctly
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the application
# We use standard streamlit run. The automation watcher will be run via supervisor or a separate worker if needed, 
# but for the main web app we just run Streamlit.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
