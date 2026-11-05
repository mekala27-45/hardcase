import threading
import time
from pathlib import Path
from hardcase.contracts import digest, file_digest, load_json, require


def verify_bundle(root):
    root = Path(root).resolve()
    manifest = load_json(root / "manifest.json")
    require(manifest.get("schema_version") == 1 and manifest.get("pooling") == "masked_mean_inside_graph" and manifest.get("normalization") == "l2_inside_graph", "UNSUPPORTED_BUNDLE_CONTRACT")
    require(manifest.get("dimension") == 384 and manifest.get("vector_dtype") == "float32", "BUNDLE_DIMENSION_OR_DTYPE")
    required = {"model.onnx", "tokenizer.json", "vectors.npy", "documents.json", "ids.json", "probe.json", "encoding-receipt.json"}
    require(required <= set(manifest.get("files", {})), "INCOMPLETE_BUNDLE")
    for name, expected in manifest["files"].items():
        target = (root / name).resolve()
        require(target.is_relative_to(root) and target.is_file(), "UNSAFE_OR_MISSING_BUNDLE_FILE")
        require(file_digest(target) == expected, "CORRUPT_BUNDLE_FILE")
    receipt = load_json(root / "encoding-receipt.json")
    require(receipt["encoder_graph_sha256"] == manifest["files"]["model.onnx"] and receipt["vectors_sha256"] == manifest["files"]["vectors.npy"] and receipt["tokenizer_sha256"] == manifest["files"]["tokenizer.json"] and receipt["corpus_digest"] == manifest["corpus_digest"], "MODEL_INDEX_MISMATCH")
    return manifest


class Bundle:
    def __init__(self, root, startup_probe=True):
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
        self.root = Path(root)
        self.manifest = verify_bundle(root)
        self.id = digest(self.manifest)
        options = ort.SessionOptions()
        options.intra_op_num_threads = self.manifest["threads"]
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(self.root / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
        require(self.session.get_providers()[0] == "CPUExecutionProvider", "UNSUPPORTED_PROVIDER")
        self.tokenizer = Tokenizer.from_file(str(self.root / "tokenizer.json"))
        self.tokenizer.enable_truncation(max_length=self.manifest["max_length"])
        self.tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", pad_type_id=0)
        self.tokenizer_lock = threading.Lock()
        self.matrix = np.load(self.root / "vectors.npy", mmap_mode="r", allow_pickle=False)
        self.ids = load_json(self.root / "ids.json")
        self.documents = load_json(self.root / "documents.json")
        require(self.matrix.dtype == np.float32 and self.matrix.shape == (len(self.ids), 384), "VECTOR_SHAPE")
        require(len(set(self.ids)) == len(self.ids) and set(self.ids) == set(self.documents), "CORPUS_ID_MISMATCH")
        require(digest(self.documents) == self.manifest["corpus_digest"], "CORPUS_DIGEST_MISMATCH")
        require(np.isfinite(self.matrix).all() and np.allclose(np.linalg.norm(self.matrix, axis=1), 1, atol=1e-4), "INVALID_DOCUMENT_VECTORS")
        self.calls = 0
        if startup_probe:
            probe = load_json(self.root / "probe.json")
            observed = self.encode(probe["texts"])
            require(np.max(np.abs(observed - np.array(probe["vectors"]))) <= probe["max_abs_error"], "STARTUP_PARITY_FAILED")

    def tokenize(self, texts):
        import numpy as np
        with self.tokenizer_lock:
            encodings = self.tokenizer.encode_batch(texts)
        data = {"input_ids": np.array([e.ids for e in encodings], dtype=np.int64), "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64), "token_type_ids": np.array([e.type_ids for e in encodings], dtype=np.int64)}
        return {i.name: data[i.name] for i in self.session.get_inputs()}

    def encode(self, texts):
        import numpy as np
        require(texts and all(isinstance(t, str) for t in texts), "INVALID_TEXT_INPUT")
        output = self.session.run(None, self.tokenize(texts))[0]
        self.calls += 1
        require(output.shape == (len(texts), 384) and np.isfinite(output).all(), "INVALID_LIVE_VECTOR")
        require(np.allclose(np.linalg.norm(output, axis=1), 1, atol=1e-4), "UNNORMALIZED_LIVE_VECTOR")
        return output

    def search(self, query, top_k=10):
        import numpy as np
        require(1 <= top_k <= 20, "TOP_K_OUT_OF_BOUNDS")
        start = time.perf_counter()
        vector = self.encode([query])[0]
        encoding_ms = (time.perf_counter() - start) * 1000
        search_start = time.perf_counter()
        scores = self.matrix @ vector
        indexes = np.lexsort((np.asarray(self.ids), -scores))[:top_k]
        results = [{"id": self.ids[int(i)], "title": self.documents[self.ids[int(i)]]["title"], "score": float(scores[i]), "visible_text": self.documents[self.ids[int(i)]]["visible_text"], "truncated": self.documents[self.ids[int(i)]]["truncated"]} for i in indexes]
        return results, {"encoding_ms": encoding_ms, "search_ms": (time.perf_counter() - search_start) * 1000, "inference_ms": (time.perf_counter() - start) * 1000}
