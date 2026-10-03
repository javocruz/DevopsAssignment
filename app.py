import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from book.routes import router as book_router
from config import get_settings
from db import get_db, get_schema_version, init_db
from intel.routes import router as intel_router
from pipeline import router as pipeline_router

app = FastAPI(title="Edgebook")
app.include_router(intel_router)
app.include_router(book_router)
app.include_router(pipeline_router)
# The dashboard links to /static/style.css. This is the only static mount.
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)


@app.get("/healthz")
def healthz(conn=Depends(get_db)):
    return {"status": "ok", "schema_version": get_schema_version(conn)}


# Startup lives here, not at import time, so importing app in tests never
# creates ./data/edgebook.db.
def main():
    settings = get_settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level)
    # TheNewsAPI puts the token in the URL, and httpx logs URLs at INFO.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    init_db()
    # 0.0.0.0 so the app is reachable from outside a container in A2.
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
