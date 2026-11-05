import os
from datetime import datetime, timezone
from hardcase.contracts import digest, require


def connect():
    import psycopg
    from psycopg.rows import dict_row
    url = os.environ.get("DATABASE_URL")
    require(bool(url) and "sslmode=" in url, "TLS_DATABASE_REQUIRED")
    return psycopg.connect(url, connect_timeout=5, row_factory=dict_row)


def alias_snapshot(name):
    with connect() as db:
        row = db.execute("SELECT a.name, a.bundle_id, a.generation, s.valid FROM hardcase.release_aliases a JOIN hardcase.bundle_status s USING (bundle_id) WHERE a.name=%s", (name,)).fetchone()
        require(row is not None, "UNKNOWN_ALIAS")
        require(row["valid"], "REVOKED_BUNDLE")
        return dict(row)


def register_bundle(manifest):
    from psycopg.types.json import Jsonb
    bundle_id = digest(manifest)
    with connect() as db:
        row = db.execute("SELECT manifest FROM hardcase.bundles WHERE id=%s", (bundle_id,)).fetchone()
        if row:
            require(row["manifest"] == manifest, "IMMUTABLE_BUNDLE_CONFLICT")
        else:
            db.execute("INSERT INTO hardcase.bundles(id,manifest) VALUES (%s,%s)", (bundle_id, Jsonb(manifest)))
            db.execute("INSERT INTO hardcase.bundle_status(bundle_id) VALUES (%s)", (bundle_id,))
    return bundle_id


def transition(proposal, available, kind="promote"):
    from psycopg.types.json import Jsonb
    require(kind in {"promote", "rollback"}, "INVALID_TRANSITION")
    for key in ("idempotency_key", "alias", "current_bundle_id", "target_bundle_id", "target_deployment_id", "evaluation_digest", "policy_digest", "proposer", "expires_at", "expected_generation"):
        require(key in proposal, "INCOMPLETE_PROPOSAL")
    require(proposal["alias"] == "default", "PROTECTED_ALIAS")
    require(proposal["target_bundle_id"] in available, "BUNDLE_NOT_PACKAGED")
    require(proposal["target_deployment_id"] == os.getenv("VERCEL_DEPLOYMENT_ID", "local"), "DEPLOYMENT_CHANGED")
    proposal_digest = digest(proposal | {"kind": kind})
    with connect() as db:
        previous = db.execute("SELECT proposal_digest,receipt FROM hardcase.release_events WHERE id=%s", (proposal["idempotency_key"],)).fetchone()
        if previous:
            require(previous["proposal_digest"] == proposal_digest, "IDEMPOTENCY_CONFLICT")
            return previous["receipt"]
        require(datetime.fromisoformat(proposal["expires_at"]) > datetime.now(timezone.utc), "EXPIRED_PROPOSAL")
        current = db.execute("SELECT * FROM hardcase.release_aliases WHERE name=%s FOR UPDATE", (proposal["alias"],)).fetchone()
        previous = db.execute("SELECT proposal_digest,receipt FROM hardcase.release_events WHERE id=%s", (proposal["idempotency_key"],)).fetchone()
        if previous:
            require(previous["proposal_digest"] == proposal_digest, "IDEMPOTENCY_CONFLICT")
            return previous["receipt"]
        require(current is not None and current["generation"] == proposal["expected_generation"] and current["bundle_id"] == proposal["current_bundle_id"], "ALIAS_GENERATION_CONFLICT")
        status = db.execute("SELECT valid FROM hardcase.bundle_status WHERE bundle_id=%s FOR SHARE", (proposal["target_bundle_id"],)).fetchone()
        require(status is not None and status["valid"], "REVOKED_OR_MISSING_TARGET")
        if kind == "promote":
            report = db.execute("SELECT report FROM hardcase.evaluation_reports WHERE id=%s", (proposal["evaluation_digest"],)).fetchone()
            require(report is not None and report["report"].get("passed") is True and report["report"].get("policy_digest") == proposal["policy_digest"] and report["report"].get("bundle_id") == proposal["target_bundle_id"], "PROMOTION_GATE_REFUSED")
        else:
            prior = db.execute("SELECT id FROM hardcase.release_events WHERE target_bundle_id=%s LIMIT 1", (proposal["target_bundle_id"],)).fetchone()
            require(prior is not None, "ROLLBACK_NOT_PREVIOUSLY_VERIFIED")
        generation = current["generation"] + 1
        receipt = {"proposal_digest": proposal_digest, "kind": kind, "alias": proposal["alias"], "previous_bundle_id": current["bundle_id"], "bundle_id": proposal["target_bundle_id"], "generation": generation, "evaluation_digest": proposal["evaluation_digest"], "deployment_id": proposal["target_deployment_id"]}
        db.execute("UPDATE hardcase.release_aliases SET bundle_id=%s,generation=%s,updated_at=now() WHERE name=%s", (proposal["target_bundle_id"], generation, proposal["alias"]))
        db.execute("INSERT INTO hardcase.release_events(id,proposal_digest,alias,previous_bundle_id,target_bundle_id,generation,kind,receipt) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (proposal["idempotency_key"], proposal_digest, proposal["alias"], current["bundle_id"], proposal["target_bundle_id"], generation, kind, Jsonb(receipt)))
    return receipt
