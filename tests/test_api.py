import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec("fastapi"), "Serving tests require the locked API environment")
class APITests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from hardcase.api.server import app
        self.client = TestClient(app)

    def test_unknown_alias_refused(self):
        response = self.client.post("/api/v1/search", json={"query": "example", "alias": "arbitrary-url"}, headers={"Authorization": "Bearer " + "a"*43, "Idempotency-Key": "test-key-123"})
        self.assertEqual(response.status_code, 422)

    def test_body_limit(self):
        response = self.client.post("/api/v1/search", content=b"x" * 8193, headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 413)

    def test_empty_query(self):
        self.assertEqual(self.client.post("/api/v1/search", json={"query": "  "}).status_code, 422)

    def test_long_unicode_query(self):
        self.assertEqual(self.client.post("/api/v1/search", json={"query": "α" * 513}).status_code, 422)

    def test_top_k_bound(self):
        self.assertEqual(self.client.post("/api/v1/search", json={"query": "example", "top_k": 21}).status_code, 422)

    def test_session_required(self):
        self.assertEqual(self.client.post("/api/v1/search", json={"query": "example"}).status_code, 401)

    def test_ops_not_public(self):
        self.assertEqual(self.client.post("/ops/promotions", json={}).status_code, 403)

    def test_no_bundle_not_ready(self):
        self.assertEqual(self.client.get("/readyz").status_code, 503)

    def test_cors_exact_origin(self):
        response = self.client.options("/api/v1/search", headers={"Origin": "https://attacker.example", "Access-Control-Request-Method": "POST"})
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_health_does_not_claim_inference(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("ready", response.json())

    def test_registered_package_and_aliases_are_required_for_readiness(self):
        from unittest.mock import MagicMock, patch
        from hardcase.api import server
        from hardcase.contracts import digest
        manifest={'method':'authored readiness fixture'}
        identity=digest(manifest)
        db=MagicMock()
        connection=MagicMock()
        connection.__enter__.return_value=db
        with patch.dict(server.bundles,{identity:object()},clear=True),patch.object(server,'startup_error',None),patch.object(server,'connect',return_value=connection):
            db.execute.return_value.fetchall.side_effect=[[]]
            self.assertEqual(self.client.get('/readyz').status_code,503)
            db.execute.return_value.fetchall.side_effect=[[{'id':identity,'manifest':manifest,'valid':True}],[{'name':name,'bundle_id':'different'} for name in ('base','default','experimental')]]
            self.assertEqual(self.client.get('/readyz').status_code,503)
            db.execute.return_value.fetchall.side_effect=[[{'id':identity,'manifest':manifest,'valid':True}],[{'name':name,'bundle_id':identity} for name in ('base','default','experimental')]]
            self.assertEqual(self.client.get('/readyz').status_code,200)
