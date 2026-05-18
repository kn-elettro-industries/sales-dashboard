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


from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)
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


@app.on_event("startup")
def _startup():
    """Startup: log that server is ready. Seed admin user from env vars if set."""
    import logging
    logging.info("ELETTRO API started. Data will load on first dashboard request.")
    # Auto-seed admin user from ADMIN_USERNAME / ADMIN_PASSWORD env vars.
    # Set these in Render → Environment to reset or create the admin account on deploy.
    admin_user = os.environ.get("ADMIN_USERNAME", "").strip()
    admin_pass = os.environ.get("ADMIN_PASSWORD", "").strip()
    if admin_user and admin_pass:
        try:
            from api.db import create_user, get_engine
            from sqlalchemy import text
            eng = get_engine()
            if eng:
                with eng.connect() as conn:
                    from api.db import _ensure_auth_users_table
                    _ensure_auth_users_table(conn)
                    existing = conn.execute(
                        text("SELECT username FROM auth_users WHERE username = :u"),
                        {"u": admin_user.lower()}
                    ).fetchone()
                    conn.commit()
                if existing:
                    # Update password
                    import bcrypt
                    pw_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
                    with eng.connect() as conn:
                        conn.execute(
                            text("UPDATE auth_users SET password_hash = :h, role = 'admin' WHERE username = :u"),
                            {"h": pw_hash, "u": admin_user.lower()}
                        )
                        conn.commit()
                    logging.info(f"STARTUP: Admin user '{admin_user}' password updated from env.")
                else:
                    err = create_user(admin_user, admin_pass, role="admin")
                    if err:
                        logging.error(f"STARTUP: Could not create admin user: {err}")
                    else:
                        logging.info(f"STARTUP: Admin user '{admin_user}' created from env.")
        except Exception as e:
            logging.error(f"STARTUP: Admin seed failed: {e}")


@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {"status": "ok", "message": "ELETTRO Intelligence API is running."}

@app.get("/version")
def version_check():
    """Diagnostic endpoint: returns fpdf version info to confirm fpdf2 is loaded."""
    import fpdf as _fpdf
    import inspect
    from fpdf import FPDF
    uses_text = 'text' in inspect.signature(FPDF.cell).parameters
    return {
        "fpdf_version": getattr(_fpdf, "__version__", "unknown"),
        "fpdf_path": getattr(_fpdf, "__file__", "unknown"),
        "cell_uses_text_param": uses_text,
        "is_fpdf2": uses_text,
    }

if __name__ == "__main__":
    import uvicorn
    # Use the PORT environment variable if available, otherwise default to 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
