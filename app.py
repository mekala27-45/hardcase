import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Hardcase", docs_url=None, redoc_url=None)


@app.get("/healthz")
def health():
    return {"status": "ok", "schema_version": 1, "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local"), "mode": "setup_probe"}


@app.get("/readyz")
def ready():
    return JSONResponse({"ready": False, "reason": "VERIFIED_BUNDLE_NOT_YET_PACKAGED"}, status_code=503)
