import tempfile
import unittest
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest
from hardcase.inference.bundle import verify_bundle


class BundleContractTests(unittest.TestCase):
    def make_fixture(self, root):
        for name in ("model.onnx", "tokenizer.json", "vectors.npy", "documents.json", "ids.json", "probe.json"):
            (root / name).write_bytes(b"synthetic contract fixture; never executable model evidence")
        receipt = {"encoder_graph_sha256": file_digest(root / "model.onnx"), "vectors_sha256": file_digest(root / "vectors.npy"), "tokenizer_sha256": file_digest(root / "tokenizer.json"), "corpus_digest": "a"*64}
        atomic_json(root / "encoding-receipt.json", receipt)
        manifest = {"schema_version": 1, "dimension": 384, "vector_dtype": "float32", "pooling": "masked_mean_inside_graph", "normalization": "l2_inside_graph", "corpus_digest": "a"*64, "files": {p.name: file_digest(p) for p in root.iterdir()}}
        atomic_json(root / "manifest.json", manifest)
        return manifest

    def test_clean_contract_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_fixture(root)
            self.assertEqual(verify_bundle(root), manifest)

    def test_corrupt_bytes_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / "model.onnx").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "CORRUPT"):
                verify_bundle(root)

    def test_model_index_mismatch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self.make_fixture(root)
            (root / "model.onnx").write_bytes(b"new encoder")
            manifest["files"]["model.onnx"] = file_digest(root / "model.onnx")
            atomic_json(root / "manifest.json", manifest)
            with self.assertRaisesRegex(ValueError, "MODEL_INDEX_MISMATCH"):
                verify_bundle(root)

    def test_missing_evidence_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            atomic_json(root / "manifest.json", {})
            with self.assertRaises(ValueError):
                verify_bundle(root)
