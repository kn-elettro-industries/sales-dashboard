from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import os
import sys
import io
import logging

# Link parent directories for v2 compatibility during transition
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import config

# Ensure data directories exist (for local dev; on Render these are ephemeral)
for folder in [config.RAW_FOLDER, config.MASTER_FOLDER, config.OUTPUT_FOLDER, config.PROCESSED_FOLDER]:
    os.makedirs(folder, exist_ok=True)

app = FastAPI(title="ELETTRO Intelligence API", version="3.0")

@app.get("/")
def home():
    return {"message": "SaaS Engine Running"}

@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy", 
        "database": "connected" if database.engine else "disconnected"
    }

from fastapi import Response

@app.get("/api/v1/data")
def get_tenant_data(tenant_id: str):
    """Fetches the processed analytics dataframe for a specific tenant."""
    df = database.load_data(tenant_id)
    if df.empty:
        return []
    
    # Serialize datetime explicitly
    if "DATE" in df.columns:
         df["DATE"] = df["DATE"].dt.strftime('%Y-%m-%d')
         
    # Return raw JSON string directly to save memory on 20,000+ rows
    json_str = df.to_json(orient="records", date_format="iso")
    return Response(content=json_str, media_type="application/json")


def process_dataframe_in_memory(df, tenant_id):
    """Runs the ETL pipeline steps in-memory (no disk I/O needed).
    This is a cloud-safe version that skips file-based operations."""
    
    try:
        import etl_pipeline
    except Exception as e:
        logging.warning(f"Could not fully import etl_pipeline (expected on cloud): {e}")
        # Even if logging setup fails, the functions are still importable
        import etl_pipeline
    
    # 1. Standardize column names
    try:
        df = etl_pipeline.standardize(df)
    except Exception as e:
        logging.warning(f"Standardize warning: {e}")
    
    # 2. Clean and Transform (filters, date enrichment)
    try:
        df = etl_pipeline.clean_and_transform(df)
    except Exception as e:
        logging.warning(f"Clean/Transform warning: {e}")

    # 3. Merge Customer Master — skip if file doesn't exist on cloud
    try:
        df = etl_pipeline.merge_customer_master(df)
    except Exception as e:
        logging.warning(f"Customer Master merge skipped (expected on cloud): {e}")
        # Ensure STATE column exists even without master
        if "STATE" not in df.columns:
            df["STATE"] = "STATE NOT FOUND"
    
    # 4. Calculate Taxes
    try:
        df = etl_pipeline.calculate_taxes(df)
    except Exception as e:
        logging.warning(f"Tax calculation warning: {e}")
    
    # 5. Write to Supabase Database
    count = etl_pipeline.update_database(df, tenant_id=tenant_id)
    
    return count



@app.post("/api/v1/upload")
async def upload_data(tenant_id: str = Form(...), file: UploadFile = File(...)):
    """Accepts an Excel file, processes it in-memory, and writes to Supabase."""
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
        logging.info(f"Read {len(df)} rows from uploaded file: {file.filename}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {e}")
        
    try:
        count = process_dataframe_in_memory(df, tenant_id)
        return {"status": "success", "message": f"Processed {count} records for {tenant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload_batch")
async def upload_batch(tenant_id: str = Form(...), files: List[UploadFile] = File(...)):
    """Accepts multiple Excel files, combines them in-memory, processes, and writes to Supabase."""
    all_dfs = []
    
    for file in files:
        try:
            contents = await file.read()
            df = pd.read_excel(io.BytesIO(contents))
            all_dfs.append(df)
            logging.info(f"Read {len(df)} rows from: {file.filename}")
        except Exception as e:
            logging.warning(f"Skipped {file.filename}: {e}")
            continue
            
    if not all_dfs:
        raise HTTPException(status_code=400, detail="No valid Excel files could be read.")
    
    # Combine all uploaded files into one DataFrame
    combined_df = pd.concat(all_dfs, ignore_index=True)
    logging.info(f"Combined {len(combined_df)} total rows from {len(all_dfs)} files")
    
    try:
        count = process_dataframe_in_memory(combined_df, tenant_id)
        return {"status": "success", "message": f"Ingested {len(all_dfs)} files, processed {count} records for {tenant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

