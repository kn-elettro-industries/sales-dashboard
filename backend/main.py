import os
import sys

# Surface startup errors so Render logs show the traceback
try:
    from fastapi import FastAPI, Request, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import asyncio
    from starlette.middleware.base import BaseHTTPMiddleware
    from api.routes import router as api_router
except Exception as e:
    print(f"Startup error: {e}", file=sys.stderr)
    sys.stderr.flush()
    raise

app = FastAPI(
    title="ELETTRO Intelligence API",
    description="FastAPI backend for ELETTRO Sales Dashboard",
    version="1.0.0"
)

# CORS: allow any origin (frontend doesn't send credentials to API).
REQUEST_TIMEOUT_SECONDS = 60


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="Request timed out. Please try again with a smaller dataset or narrower filters.")


class CorsAllMiddleware(BaseHTTPMiddleware):
    """Ensure CORS headers on every response so browser never sees 'No Access-Control-Allow-Origin'."""
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            from starlette.responses import Response
            return Response(
                status_code=200,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Max-Age": "86400",
                },
            )
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response


app.add_middleware(CorsAllMiddleware)
app.add_middleware(TimeoutMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

app.include_router(api_router, prefix="/api")

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "ok", "message": "ELETTRO Intelligence API is running."}

if __name__ == "__main__":
    import uvicorn
    # Use the PORT environment variable if available, otherwise default to 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
