import json
import os
import time
import config

STATUS_FILE = os.path.join(config.OUTPUT_FOLDER, "pipeline_status.json")

def update_status(step, status, details="", progress=0):
    """
    Updates the pipeline status file.
    step: Current step name (e.g., "Ingest", "Transform")
    status: "Running", "Completed", "Failed", "Idle"
    details: Description of current action
    progress: 0-100 percentage
    """
    data = {
        "step": step,
        "status": status,
        "details": details,
        "progress": progress,
        "timestamp": time.time()
    }
    
    with open(STATUS_FILE, "w") as f:
        json.dump(data, f)

def get_status():
    """Reads the current pipeline status."""
    if not os.path.exists(STATUS_FILE):
        return {"step": "Idle", "status": "Idle", "details": "Waiting for trigger...", "progress": 0}
    
    try:
        with open(STATUS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"step": "Error", "status": "Unknown", "details": "Could not read status", "progress": 0}

def reset_status():
    """Resets the status to Idle."""
    update_status("Idle", "Idle", "System Ready", 0)
