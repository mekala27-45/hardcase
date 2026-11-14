import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from hardcase.contracts import digest, require
from hardcase.registry.postgres import connect


def capability_digest(capability):
    require(isinstance(capability, str) and 40 <= len(capability) <= 100, "INVALID_SESSION")
    return hashlib.sha256(capability.encode()).hexdigest()


def new_session():
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(2701001)")
        count = db.execute("SELECT count(*) AS n FROM hardcase.sessions WHERE created_at > now() - interval '1 minute'").fetchone()["n"]
        require(count < 30, "SESSION_RATE_LIMIT")
        db.execute("INSERT INTO hardcase.sessions(capability_digest,expires_at) VALUES (%s,%s)", (capability_digest(token), expires))
    return {"capability": token, "expires_at": expires.isoformat()}


def admit(token, key, payload):
    session_digest = capability_digest(token)
    request_digest = digest(payload)
    with connect() as db:
        session = db.execute("SELECT * FROM hardcase.sessions WHERE capability_digest=%s FOR UPDATE", (session_digest,)).fetchone()
        require(session is not None and session["expires_at"] > datetime.now(timezone.utc), "EXPIRED_OR_INVALID_SESSION")
        old = db.execute("SELECT * FROM hardcase.query_receipts WHERE session_digest=%s AND idempotency_key=%s", (session_digest, key)).fetchone()
        if old:
            require(old["request_digest"] == request_digest, "IDEMPOTENCY_CONFLICT")
            require(old["status"] == "completed", "REQUEST_PENDING_OR_FAILED")
            current = db.execute("SELECT valid FROM hardcase.bundle_status WHERE bundle_id=%s", (old["bundle_id"],)).fetchone()
            require(current is not None and current["valid"], "BUNDLE_REVOKED_BEFORE_REPLAY")
            return {"replayed": True, "receipt": old["receipt"]}
        require(not session["busy_request"] or session["busy_until"] < datetime.now(timezone.utc), "SESSION_BUSY")
        if session['busy_request']:
            db.execute("UPDATE hardcase.query_receipts SET status='timeout',completed_at=now(),receipt=jsonb_build_object('id',id,'bundle_id',bundle_id,'admission_generation',admission_generation,'status','timeout','error','WORKER_LEASE_EXPIRED','results','[]'::jsonb,'fresh',false) WHERE id=%s AND status='pending'", (session['busy_request'],))
        snapshot = db.execute("SELECT a.bundle_id,a.generation,s.valid FROM hardcase.release_aliases a JOIN hardcase.bundle_status s USING(bundle_id) WHERE a.name=%s", (payload["alias"],)).fetchone()
        require(snapshot is not None and snapshot["valid"], "UNAVAILABLE_ALIAS")
        request_id = str(uuid.uuid4())
        db.execute("UPDATE hardcase.sessions SET busy_request=%s,busy_until=now()+interval '60 seconds' WHERE capability_digest=%s", (request_id, session_digest))
        db.execute("INSERT INTO hardcase.query_receipts(id,session_digest,idempotency_key,request_digest,bundle_id,admission_generation,status) VALUES (%s,%s,%s,%s,%s,%s,'pending')", (request_id, session_digest, key, request_digest, snapshot["bundle_id"], snapshot["generation"]))
    return {"replayed": False, "request_id": request_id, "session_digest": session_digest, "request_digest": request_digest, **dict(snapshot)}


def commit_receipt(admission, receipt, status="completed"):
    from psycopg.types.json import Jsonb
    revoked = False
    with connect() as db:
        row = db.execute("SELECT valid FROM hardcase.bundle_status WHERE bundle_id=%s FOR SHARE", (admission["bundle_id"],)).fetchone()
        revoked = row is None or not row["valid"]
        final_status = "revoked" if revoked else status
        latest = db.execute("SELECT generation FROM hardcase.release_aliases WHERE name=%s", (receipt["alias"],)).fetchone()
        receipt["completion_generation"] = latest["generation"] if latest else None
        receipt["status"] = final_status
        if final_status != "completed":
            receipt["results"] = []
            receipt["top_document_ids"] = []
        updated = db.execute("UPDATE hardcase.query_receipts SET status=%s,receipt=%s,completed_at=now() WHERE id=%s AND status='pending'", (final_status, Jsonb(receipt), admission["request_id"]))
        require(updated.rowcount == 1, 'RECEIPT_ALREADY_TERMINAL')
        db.execute("UPDATE hardcase.sessions SET busy_request=NULL,busy_until=NULL WHERE capability_digest=%s AND busy_request=%s", (admission["session_digest"], admission["request_id"]))
    require(not revoked, "BUNDLE_REVOKED_BEFORE_COMMIT")
    return receipt


def read_receipt(token, request_id):
    session_digest = capability_digest(token)
    with connect() as db:
        row = db.execute("SELECT q.receipt FROM hardcase.query_receipts q JOIN hardcase.sessions s ON s.capability_digest=q.session_digest JOIN hardcase.bundle_status b ON b.bundle_id=q.bundle_id WHERE q.id=%s AND q.session_digest=%s AND s.expires_at>now() AND q.status='completed' AND b.valid", (request_id, session_digest)).fetchone()
    require(row is not None, "RECEIPT_NOT_FOUND")
    return row["receipt"]
