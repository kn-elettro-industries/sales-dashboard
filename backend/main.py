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
    """Startup: ensure at least one admin exists. Creates/resets from env vars, or auto-creates if DB is empty."""
    import logging
    logging.info("ELETTRO API started. Data will load on first dashboard request.")
    try:
        from api.db import create_user, get_engine, _ensure_auth_users_table
        from sqlalchemy import text
        import bcrypt

        admin_user = os.environ.get("ADMIN_USERNAME", "admin").strip().lower()
        admin_pass = os.environ.get("ADMIN_PASSWORD", "").strip()

        eng = get_engine()
        if not eng:
            logging.error("STARTUP: DB unavailable — cannot seed admin user.")
            return

        with eng.connect() as conn:
            _ensure_auth_users_table(conn)
            any_admin = conn.execute(
                text("SELECT username FROM auth_users WHERE role = 'admin' LIMIT 1")
            ).fetchone()
            conn.commit()

        if admin_pass:
            # Env var set: always upsert that specific user with the given password
            pw_hash = bcrypt.hashpw(admin_pass.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            with eng.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO auth_users (username, password_hash, role, tenant)
                        VALUES (:u, :h, 'admin', 'default_elettro')
                        ON CONFLICT (username) DO UPDATE SET password_hash = :h, role = 'admin'
                    """),
                    {"u": admin_user, "h": pw_hash}
                )
                conn.commit()
            logging.info(f"STARTUP: Admin user '{admin_user}' upserted from env vars.")
        elif not any_admin:
            # No admin exists and no env var — create default so the app is never locked out
            default_pass = "Admin@1234"
            err = create_user(admin_user, default_pass, role="admin")
            if err:
                logging.error(f"STARTUP: Could not auto-create admin: {err}")
            else:
                logging.warning(
                    f"STARTUP: No admin found — created '{admin_user}' with default password '{default_pass}'. "
                    "Change it immediately via Add User page."
                )
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
