import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from book.config import get_settings
from book.db import get_db, get_schema_version, init_db
from book.routes import router as book_router

app = FastAPI(title="Edgebook Book")
app.include_router(book_router)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)


@app.get("/healthz")
def healthz(conn=Depends(get_db)):
    return {"status": "ok", "schema_version": get_schema_version(conn)}


def main():
    settings = get_settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=settings.port)


if __name__ == "__main__":
    main()
