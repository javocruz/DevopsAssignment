import logging
import sys

import uvicorn
from fastapi import Depends, FastAPI

from intel.config import get_settings
from intel.db import get_db, get_schema_version, init_db
from intel.routes import router as intel_router

app = FastAPI(title="Edgebook Intel")
app.include_router(intel_router)


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
