from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_digest(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temporary.open("wb") as stream:
        stream.write(canonical(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def require(condition, code):
    if not condition:
        raise ValueError(code)


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


class Stage:
    def __init__(self, root, name, inputs):
        self.path = Path(root) / f"{name}.json"
        self.record = {"stage": name, "status": "running", "started_at": utcnow(), "inputs": inputs, "input_digest": digest(inputs), "source_commit": os.getenv("GITHUB_SHA", "local"), "run_id": os.getenv("GITHUB_RUN_ID", "local")}

    def __enter__(self):
        atomic_json(self.path, self.record)
        return self.record

    def __exit__(self, typ, err, traceback):
        self.record.update(status="failed" if err else "completed", ended_at=utcnow())
        if err:
            self.record["error"] = {"type": typ.__name__, "code": str(err)[:400]}
        atomic_json(self.path, self.record)
        return False
