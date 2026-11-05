---
name: promote-model-bundle
description: Review a concrete Hardcase promotion or rollback against immutable bundle identity, live deployment, measured gates and current alias generation.
---

Read AGENTS.md and OPERATIONS.md. Require an actual hashed serving package, observed deployment ID, complete evaluation report and measured serving envelope. Read the current default bundle and generation through a new database connection. Public sessions have no operator authority.

Calculate `hardcase.registry.gates.release_gate` from observed evidence and the frozen promotion policy. A failed or missing gate keeps the base default. Register an immutable report with its canonical digest. Prepare the proposal fields required by `hardcase.registry.postgres.transition`, including target deployment, expiry, proposer, current bundle, target bundle, report/policy digests, expected generation and a new idempotency key.

Use the protected POST /ops/promotions endpoint only within the current authorization. Inspect its committed receipt. Submit a fresh request and independently read the database to confirm the actual target bundle and new generation. A CAS conflict requires a fresh review, not a blind retry with an updated generation. An identical proposal retry must return its prior receipt.

For rollback, use POST /ops/rollback to a retained verified allowlisted bundle. Verify a fresh request and new DB read after the action. Ordinary rollback allows an admitted request to finish with its captured valid bundle. Integrity revocation blocks new admissions and refuses the final receipt commit. Stop on missing credentials, absent authorization, revoked or incompatible artifacts, expired proposals or unverified recovery.
