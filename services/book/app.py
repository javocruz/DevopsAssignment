import logging
import os
import sqlite3
import sys
import time
import uuid
from pathlib import Path

import book.db as database
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from book.config import get_settings
from book.db import init_db
from book.routes import router as book_router

access_log = logging.getLogger("edgebook.access")

app = FastAPI(title="Edgebook Book")
app.include_router(book_router)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        access_log.info(
            "%s %s %s %.1fms %s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        return response


def add_cors(application):
    raw = os.environ.get("CORS_ORIGINS", "")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["Content-Type", "X-Admin-Token", "X-Request-ID"],
    )


app.add_middleware(RequestLogMiddleware)
add_cors(app)


@app.get("/health")
def health():
    version = os.environ.get("GIT_SHA", "dev")
    try:
        conn = database.get_connection()
        try:
            conn.execute("SELECT 1").fetchone()
            conn.execute("UPDATE bets SET id = id WHERE 0")
        finally:
            conn.close()
    except sqlite3.Error:
        return JSONResponse(
            status_code=503,
            content={"status": "down", "db": "down", "version": version},
        )
    return {"status": "ok", "db": "ok", "version": version}


def main():
    settings = get_settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
