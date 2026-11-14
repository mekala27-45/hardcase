# Hardcase live deployment

Verified 2026-11-14 UTC after Ajay explicitly authorized initializing the prepared Neon registry, storing database and operator credentials in Hardcase production and preview, and enabling public demo access with protected operator endpoints.

Public workbench: https://mekala27-45.github.io/hardcase/
Public API: https://hardcase-taupe.vercel.app
Verified source: `9e413f9479732f92acc0a1ab1b240bf32a43b01c`
Verified deployment: `dpl_EogbfiZVonSLZU97reMvh1KNsgDg`
Passing frontend build, responsive/theme tests and Pages publication: https://github.com/mekala27-45/hardcase/actions/runs/43544865159

The prepared transaction initialized two models, two valid bundles, three aliases and three initialization events. Base and default remain the pretrained bundle at generation 1. Experimental points to the trained float32 bundle. DATABASE_URL and OPERATOR_TOKEN are sensitive Vercel variables targeted to production and preview. No secret values are retained in this evidence.

Anonymous readiness and experimental HTTP search succeeded. The public browser workbench returned ten results and its persisted-receipt confirmation succeeded. Both operator endpoints rejected missing, invalid and public-session credentials. Existing Vercel Standard Protection was retained: the production domain is public, generated production and preview URLs redirect to login. An unnecessary proposed protection change was rejected by automatic approval review and was not executed or retried.

The repository's unchanged deploy/verify_live.py passed on the independently captured browser download, separate HTTP response, fresh Neon readback, and retained runtime package. See evidence/live/pretest.json and its raw inputs. An initial Windows console import replaced a Greek letter; the verifier correctly refused it. Reading the original browser JSON file directly as UTF-8 resolved the transport issue without changing the receipt or relaxing the verifier.

This establishes live serving and protected operations, not held-out model quality or promotion. Next follow the frozen evaluation procedure: bind the verified pretest digest, restore the original training checkpoints and the accepted float32 compatibility archive separately, retain the rejected INT8 attempt, complete all planned held-out rows and serving checks, and calculate release gates. No held-out evaluation or promotion was performed in this deployment step. No operator key rotation, billing changes or exposure of preview URLs is required.


## Subsequent verification

A separate proof set in evidence/live/release-20261114/ verifies browser and client receipts for deployment `dpl_CSHM7YARPRJLj467t5UwSry53Yv6`, serving source `728a25e88931d98aa0ae960c9b246c38efee1050`. The bounded public smoke and all receipt readbacks use that same deployment. requests/release-check.json pins these proof digests without replacing the original pretest. The first held-out evaluation request is now admitted; its outcomes are reported separately under evidence/evaluation when retained.
