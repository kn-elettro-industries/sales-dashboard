# Sales Pipeline (Experiment)

## Overview
This repository contains the sales dashboard and ETL pipeline for K.N. Elettro.
The project is structured to separate core application logic, data processing, and analytical modules.

## Project Structure

### Core Application
*   `app.py`: Main entry point for the Streamlit dashboard.
*   `auth.py`: Authentication and RBAC implementation.
*   `config.py`: Configuration settings (paths, constants).
*   `etl_pipeline.py`: Data ingestion and transformation logic.
*   `watcher.py`: Background service to monitor input folders.

### Modules
*   `analytics/`: Contains business logic for data visualization and reporting.
    *   `reporting.py`: PDF generation and daily archival.
    *   `chatbot.py`: Natural Language Processing (NLP) engine for "Krishiv".
    *   `advanced.py`: Map visualizations and scatter plots.
*   `assets/`: Static assets (CSS, Images, GeoJSON data).
*   `data/`: Storage for processed data (Parquet/Excel) and raw inputs.
*   `scripts/`: Utility scripts for maintenance (Database checks, Debugging).

### Documentation
*   `engineering_journal/`: Daily logs of technical implementation decisions.

## Setup
1.  Install dependencies: `pip install -r requirements.txt`
2.  Run the application: `streamlit run app.py`
