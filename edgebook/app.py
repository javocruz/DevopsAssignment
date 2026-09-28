import logging
import sys

import uvicorn
from fastapi import Depends, FastAPI

from config import get_settings
from db import get_db, get_schema_version, init_db

app = FastAPI(title="Edgebook")


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
