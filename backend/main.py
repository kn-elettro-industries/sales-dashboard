from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from api.routes import router as api_router

app = FastAPI(
    title="ELETTRO Intelligence API",
    description="FastAPI backend for ELETTRO Sales Dashboard",
    version="1.0.0"
)

# Allow CORS for local Next.js dev server and Vercel domains
origins = [
    "http://localhost:3000",
    "https://dashboard.elettro.in",
    "*"  # Allows all origins for testing. In prod, restrict this!
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "ELETTRO Intelligence API is running."}

if __name__ == "__main__":
    import uvicorn
    # Use the PORT environment variable if available, otherwise default to 8000
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
