CREATE SCHEMA IF NOT EXISTS hardcase;
CREATE TABLE IF NOT EXISTS hardcase.model_versions (
  id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
  manifest jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.bundles (
  id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
  manifest jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.bundle_status (
  bundle_id text PRIMARY KEY REFERENCES hardcase.bundles(id),
  valid boolean NOT NULL DEFAULT true,
  reason text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.evaluation_reports (
  id text PRIMARY KEY CHECK (id ~ '^[0-9a-f]{64}$'),
  report jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.release_aliases (
  name text PRIMARY KEY CHECK (name IN ('base', 'experimental', 'default')),
  bundle_id text NOT NULL REFERENCES hardcase.bundles(id),
  generation bigint NOT NULL CHECK (generation > 0),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.release_events (
  id text PRIMARY KEY,
  proposal_digest text NOT NULL,
  alias text NOT NULL,
  previous_bundle_id text,
  target_bundle_id text NOT NULL REFERENCES hardcase.bundles(id),
  generation bigint NOT NULL,
  kind text NOT NULL CHECK (kind IN ('initialize', 'promote', 'rollback')),
  receipt jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (alias, generation)
);
CREATE TABLE IF NOT EXISTS hardcase.sessions (
  capability_digest text PRIMARY KEY CHECK (capability_digest ~ '^[0-9a-f]{64}$'),
  expires_at timestamptz NOT NULL,
  busy_request text,
  busy_until timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS hardcase.query_receipts (
  id text PRIMARY KEY,
  session_digest text NOT NULL REFERENCES hardcase.sessions(capability_digest),
  idempotency_key text NOT NULL,
  request_digest text NOT NULL,
  bundle_id text NOT NULL REFERENCES hardcase.bundles(id),
  admission_generation bigint NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'completed', 'failed', 'timeout', 'revoked')),
  receipt jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  UNIQUE (session_digest, idempotency_key)
);
CREATE INDEX IF NOT EXISTS receipt_session_created ON hardcase.query_receipts(session_digest, created_at);
CREATE TABLE IF NOT EXISTS hardcase.job_receipts (
  id text PRIMARY KEY,
  receipt jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE OR REPLACE FUNCTION hardcase.reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'IMMUTABLE_EVIDENCE';
END;
$$;
DO $$
DECLARE table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY['model_versions','bundles','evaluation_reports','release_events','job_receipts'] LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'immutable_' || table_name AND tgrelid = ('hardcase.' || table_name)::regclass) THEN
      EXECUTE format('CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON hardcase.%I FOR EACH ROW EXECUTE FUNCTION hardcase.reject_immutable_change()', 'immutable_' || table_name, table_name);
    END IF;
  END LOOP;
END;
$$;
