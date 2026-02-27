from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import os
import sys

# Link parent directories for v2 compatibility during transition
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database
import etl_pipeline
import config

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

@app.post("/api/v1/upload")
async def upload_data(tenant_id: str = Form(...), file: UploadFile = File(...)):
    """Accepts an Excel file from the UI, saves it, and triggers the Pipeline."""
    save_path = os.path.join(config.RAW_FOLDER, file.filename)
    
    try:
        contents = await file.read()
        with open(save_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
        
    # Trigger isolated ETL Pipeline for this tenant
    try:
        etl_pipeline.run_pipeline(tenant_id)
        return {"status": "success", "message": f"Data ingested and processed for {tenant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/upload_batch")
async def upload_batch(tenant_id: str = Form(...), files: List[UploadFile] = File(...)):
    """Accepts multiple Excel files from the UI, saves them all, and triggers the Pipeline ONCE."""
    saved_count = 0
    for file in files:
        save_path = os.path.join(config.RAW_FOLDER, file.filename)
        try:
            contents = await file.read()
            with open(save_path, "wb") as f:
                f.write(contents)
            saved_count += 1
        except Exception:
            continue
            
    if saved_count == 0:
        raise HTTPException(status_code=400, detail="No files could be saved.")
        
    # Trigger isolated ETL Pipeline ONCE for this tenant
    try:
        etl_pipeline.run_pipeline(tenant_id)
        return {"status": "success", "message": f"Ingested {saved_count} files and processed data for {tenant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
