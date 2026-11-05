import asyncio
import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Literal
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from hardcase.contracts import digest, load_json, require, utcnow
from hardcase.inference.bundle import Bundle
from hardcase.registry.postgres import connect, transition
from .receipts import new_session, admit, commit_receipt, read_receipt

ROOT = Path(os.environ.get("HARDCASE_BUNDLE_ROOT", "runtime/bundles"))
bundles = {}
startup_error = None
pending_tasks = set()


@asynccontextmanager
async def lifespan(app):
    global startup_error
    startup_error = None
    bundles.clear()
    try:
        package = load_json(ROOT / "allowlist.json")
        require(1 <= len(package["bundles"]) <= 3, "PACKAGED_BUNDLE_LIMIT")
        for row in package["bundles"]:
            path = (ROOT / row["directory"]).resolve()
            require(path.is_relative_to(ROOT.resolve()), "BUNDLE_PATH_ESCAPE")
            bundle = Bundle(path)
            require(bundle.id == row["id"], "ALLOWLIST_ID_MISMATCH")
            bundles[bundle.id] = bundle
    except Exception as error:
        bundles.clear()
        startup_error = type(error).__name__ + ": " + str(error)[:200]
    yield


app = FastAPI(title="Hardcase", docs_url=None, redoc_url=None, lifespan=lifespan)
origins = [s.strip() for s in os.environ.get("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,https://mekala27-45.github.io").split(",") if s.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type", "Authorization", "Idempotency-Key"])


class BodyLimit:
    def __init__(self, app):
        self.application = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.application(scope, receive, send)
        chunks, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 8192:
                return await JSONResponse({"detail": "BODY_TOO_LARGE"}, status_code=413)(scope, receive, send)
            chunks.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(chunks)
        async def replay():
            return next(iterator, {"type": "http.request", "body": b"", "more_body": False})
        await self.application(scope, replay, send)


app.add_middleware(BodyLimit)


class Search(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    query: str = Field(min_length=1, max_length=512)
    alias: Literal["base", "experimental", "default"] = "default"
    top_k: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def nonempty(cls, value):
        if not value.strip():
            raise ValueError("EMPTY_NORMALIZED_QUERY")
        return value.strip()


def capability(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "SESSION_REQUIRED")
    return authorization[7:]


@app.exception_handler(ValueError)
async def refusal(request, error):
    code = str(error)
    status = 409 if any(s in code for s in ("CONFLICT", "PENDING", "BUSY", "GENERATION")) else 401 if "SESSION" in code else 404 if "NOT_FOUND" in code else 429 if "RATE_LIMIT" in code else 503
    return JSONResponse({"detail": code}, status_code=status)


@app.get("/healthz")
def health():
    return {"status": "ok", "schema_version": 1, "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local")}


@app.get("/readyz")
def ready():
    if startup_error or not bundles:
        return JSONResponse({"ready": False, "reason": "BUNDLE_STARTUP_FAILED", "diagnostic": startup_error}, status_code=503)
    try:
        with connect() as db:
            db.execute("SELECT 1 FROM hardcase.bundles LIMIT 1")
    except Exception:
        return JSONResponse({"ready": False, "reason": "DATABASE_UNREACHABLE"}, status_code=503)
    return {"ready": True, "bundles": sorted(bundles), "commit": os.getenv("VERCEL_GIT_COMMIT_SHA", "local")}


@app.get("/api/v1/models")
def models():
    with connect() as db:
        aliases = db.execute("SELECT a.name,a.bundle_id,a.generation,s.valid FROM hardcase.release_aliases a JOIN hardcase.bundle_status s USING(bundle_id) ORDER BY a.name").fetchall()
    return {"aliases": [dict(r) | {"available": r["bundle_id"] in bundles and r["valid"], "experimental": r["name"] == "experimental"} for r in aliases]}


@app.post("/api/v1/sessions")
def sessions():
    require(bool(bundles), "MODEL_UNAVAILABLE")
    return new_session()


def execute_search(payload, token, key):
    start = time.perf_counter()
    request_identity = {"query_digest": hashlib.sha256(payload.query.encode()).hexdigest(), "alias": payload.alias, "top_k": payload.top_k}
    admission = admit(token, key, request_identity)
    if admission["replayed"]:
        return admission["receipt"] | {"replayed": True, "fresh": False}
    receipt = {"id": admission["request_id"], "alias": payload.alias, "bundle_id": admission["bundle_id"], "admission_generation": admission["generation"], "query_digest": request_identity["query_digest"], "request_digest": admission["request_digest"], "fresh": True, "replayed": False, "namespace": "live_request", "observed_at": utcnow(), "deployment_id": os.getenv("VERCEL_DEPLOYMENT_ID", "local")}
    try:
        bundle = bundles.get(admission["bundle_id"])
        require(bundle is not None, "MODEL_UNAVAILABLE")
        results, stages = bundle.search(payload.query, payload.top_k)
        serialize_start = time.perf_counter()
        json.dumps(results, allow_nan=False)
        stages["serialization_ms"] = (time.perf_counter() - serialize_start) * 1000
        stages["elapsed_before_receipt_ms"] = (time.perf_counter() - start) * 1000
        receipt.update(results=results, top_document_ids=[r["id"] for r in results], timings=stages, graph_digest=bundle.manifest["files"]["model.onnx"], tokenizer_digest=bundle.manifest["files"]["tokenizer.json"], corpus_digest=bundle.manifest["corpus_digest"], index_digest=bundle.manifest["files"]["vectors.npy"])
        if time.perf_counter() - start > 10:
            commit_receipt(admission, receipt, "timeout")
            raise HTTPException(504, "SEARCH_DEADLINE")
        return commit_receipt(admission, receipt)
    except HTTPException:
        raise
    except Exception as error:
        receipt["error"] = type(error).__name__
        try:
            commit_receipt(admission, receipt, "failed")
        except Exception:
            pass
        raise


@app.post("/api/v1/search")
async def search(payload: Search, authorization: str | None = Header(default=None), idempotency_key: str | None = Header(default=None)):
    token = capability(authorization)
    if not idempotency_key or not 8 <= len(idempotency_key) <= 128:
        raise HTTPException(422, "IDEMPOTENCY_KEY_REQUIRED")
    task = asyncio.create_task(asyncio.to_thread(execute_search, payload, token, idempotency_key))
    pending_tasks.add(task)
    task.add_done_callback(pending_tasks.discard)
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout=10)
    except asyncio.TimeoutError:
        raise HTTPException(504, "SEARCH_DEADLINE")


@app.get("/api/v1/receipts/{request_id}")
def receipts(request_id: str, authorization: str | None = Header(default=None)):
    return read_receipt(capability(authorization), request_id)


@app.get("/api/v1/documents/{document_id}")
def documents(document_id: str):
    require(bool(bundles), "MODEL_UNAVAILABLE")
    document = next(iter(bundles.values())).documents.get(document_id)
    if not document:
        raise HTTPException(404, "DOCUMENT_NOT_FOUND")
    return document


@app.get("/api/v1/experiments/latest")
def experiment():
    path = Path("runtime/report.json")
    return load_json(path) if path.exists() else {"status": "pending", "message": "Final held-out evaluation is not yet available."}


def operator(authorization):
    expected = os.environ.get("OPERATOR_TOKEN")
    if not expected or not hmac.compare_digest(capability(authorization), expected):
        raise HTTPException(403, "OPERATOR_REQUIRED")


@app.post("/ops/promotions")
def promote(proposal: dict, authorization: str | None = Header(default=None)):
    operator(authorization)
    return transition(proposal, set(bundles), "promote")


@app.post("/ops/rollback")
def rollback(proposal: dict, authorization: str | None = Header(default=None)):
    operator(authorization)
    return transition(proposal, set(bundles), "rollback")
