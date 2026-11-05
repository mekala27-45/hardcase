import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from hardcase.contracts import Stage, atomic_json, digest, file_digest, load_json, require, utcnow
from hardcase.training.encoder import download_locked, load_encoder, pool, encode, parameter_hashes
from hardcase.inference.bundle import Bundle
from hardcase.mining.retrieval import exact_search
from evaluation.metrics import grade, qrel_map


def export_graph(model, tokenizer, destination, max_length):
    import torch
    class Pooled(torch.nn.Module):
        def __init__(self, model):
            super().__init__()
            self.model = model
        def forward(self, input_ids, attention_mask, token_type_ids):
            return pool(self.model, {"input_ids": input_ids, "attention_mask": attention_mask, "token_type_ids": token_type_ids})
    model.eval()
    batch = tokenizer(["Scientific observations.", "No change was observed at 10 mg."], padding=True, truncation=True, max_length=max_length, return_tensors="pt")
    keys = ["input_ids", "attention_mask", "token_type_ids"]
    torch.onnx.export(Pooled(model).eval(), tuple(batch[k] for k in keys), str(destination), input_names=keys, output_names=["embeddings"], dynamic_axes={k: {0: "batch", 1: "sequence"} for k in keys} | {"embeddings": {0: "batch"}}, opset_version=18, dynamo=False)


def graph_encoder(graph_path, tokenizer_path, max_length):
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(graph_path), sess_options=options, providers=["CPUExecutionProvider"])
    tokenizer = Tokenizer.from_file(str(tokenizer_path))
    tokenizer.enable_truncation(max_length=max_length)
    tokenizer.enable_padding(pad_id=0, pad_token="[PAD]", pad_type_id=0)
    def tokens(texts):
        batch = tokenizer.encode_batch(texts)
        return {"input_ids": np.array([r.ids for r in batch], dtype=np.int64), "attention_mask": np.array([r.attention_mask for r in batch], dtype=np.int64), "token_type_ids": np.array([r.type_ids for r in batch], dtype=np.int64)}
    def infer(texts):
        batch = tokens(texts)
        return session.run(None, {x.name: batch[x.name] for x in session.get_inputs()})[0]
    return infer, tokens


def make_bundle(method, graph, tokenizer, parent_digest, documents, config):
    import numpy as np
    root = Path("artifacts/bundles") / method
    root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(graph, root / "model.onnx")
    shutil.copy2(tokenizer, root / "tokenizer.json")
    infer, _ = graph_encoder(root / "model.onnx", root / "tokenizer.json", config["max_length"])
    ids = sorted(documents)
    started = utcnow()
    timer = time.perf_counter()
    matrix = np.concatenate([infer([documents[d]["visible_text"] for d in ids[i:i+16]]) for i in range(0, len(ids), 16)]).astype(np.float32)
    require(matrix.shape == (len(ids), 384) and np.isfinite(matrix).all(), "EXPORT_CORPUS_ENCODING")
    np.save(root / "vectors.npy", matrix, allow_pickle=False)
    atomic_json(root / "documents.json", documents)
    atomic_json(root / "ids.json", ids)
    probe_texts = ["No change was observed.", "A randomized trial measured protein expression."]
    atomic_json(root / "probe.json", {"texts": probe_texts, "vectors": infer(probe_texts).tolist(), "max_abs_error": 1e-5})
    receipt = {"encoder_graph_sha256": file_digest(root / "model.onnx"), "vectors_sha256": file_digest(root / "vectors.npy"), "tokenizer_sha256": file_digest(root / "tokenizer.json"), "corpus_digest": digest(documents), "rows": len(ids), "started_at": started, "ended_at": utcnow(), "seconds": time.perf_counter() - timer, "mode": "actual_onnx_symmetric_encoding"}
    atomic_json(root / "encoding-receipt.json", receipt)
    manifest = {"schema_version": 1, "method": method, "parent_state_digest": parent_digest, "files": {p.name: file_digest(p) for p in sorted(root.iterdir()) if p.is_file() and p.name != "manifest.json"}, "max_length": config["max_length"], "dimension": 384, "vector_dtype": "float32", "pooling": "masked_mean_inside_graph", "normalization": "l2_inside_graph", "text_normalization": "NFC_CRLF_to_LF_strip_title_double_newline_abstract", "corpus_digest": digest(documents), "ids_digest": digest(ids), "threads": 2, "provider": "CPUExecutionProvider", "opset": 18, "config_digest": digest(config)}
    atomic_json(root / "manifest.json", manifest)
    return root


def build():
    import numpy as np
    import torch
    from onnxruntime.quantization import QuantType, quantize_dynamic
    config = load_json("requests/experiment.json")
    selection = load_json("artifacts/training/selection.json")
    require(selection["state"] == "selected_on_validation_before_test", "MISSING_VALIDATION_SELECTION")
    documents = load_json("data/processed/documents.json")
    split = load_json("data/manifests/split.json")
    queries = load_json("data/processed/train-queries.json")
    gold = qrel_map(load_json("data/processed/train-qrels.json"))
    root = Path("artifacts/export")
    root.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(2)
    with Stage(root, "export", {"selection_id": selection["selection_id"], "config": digest(config)}) as report:
        parity_ids = []
        for partition in ("fit", "validation"):
            ordered = sorted(split[partition], key=lambda q: (len(queries[q]["text"]), digest(q)))
            parity_ids.extend([ordered[min(len(ordered)-1, int(i * len(ordered) / min(32, len(ordered))))] for i in range(min(32, len(ordered)))])
        parity_texts = [queries[q]["text"] for q in parity_ids] + ["", "x", "alpha-beta: 10 mg; no effect.", "Unicode: α β μg café", "protein " * 400]
        timing_ids = sorted(split["validation"], key=lambda q: (len(queries[q]["text"]), digest(q)))
        timing_ids = [timing_ids[min(len(timing_ids)-1, int(i * len(timing_ids) / min(30, len(timing_ids))))] for i in range(min(30, len(timing_ids)))]
        atomic_json(root / "timing-queries.json", [{"id": q, "text": queries[q]["text"]} for q in timing_ids])
        paths = {"base_float32": download_locked("student"), "candidate_float32": Path(selection["candidate"]["checkpoint"]) / "encoder"}
        parity_results = {}
        bundles = {}
        for method, path in paths.items():
            model, tokenizer = load_encoder(path)
            graph = root / f"{method}.onnx"
            export_graph(model, tokenizer, graph, config["max_length"])
            infer, tokens = graph_encoder(graph, path / "tokenizer.json", config["max_length"])
            reference_tokens = tokenizer(parity_texts, padding=True, truncation=True, max_length=config["max_length"], return_tensors="np")
            observed_tokens = tokens(parity_texts)
            require(all(np.array_equal(reference_tokens[k], observed_tokens[k]) for k in observed_tokens), "EXPORT_TOKEN_PARITY")
            expected = encode(model, tokenizer, parity_texts, config["max_length"], batch_size=len(parity_texts))
            observed = infer(parity_texts)
            errors = np.max(np.abs(expected - observed), axis=1)
            distances = 1 - (expected * observed).sum(axis=1)
            require(np.all(errors <= config["export"]["max_abs_error"]) and np.all(distances <= config["export"]["max_cosine_distance"]), "FLOAT32_PARITY_FAILED")
            parent = digest(parameter_hashes(model))
            parity_results[method] = {"status": "completed", "token_parity": True, "input_digest": digest(parity_texts), "benchmark_query_ids": parity_ids, "synthetic_edge_cases": 5, "max_abs_errors": errors.tolist(), "cosine_distances": distances.tolist(), "parent_state_digest": parent, "graph_sha256": file_digest(graph)}
            bundles[method] = str(make_bundle(method, graph, path / "tokenizer.json", parent, documents, config))
            if method == "candidate_float32":
                try:
                    quantized = root / "candidate_int8.onnx"
                    quantize_dynamic(str(graph), str(quantized), weight_type=QuantType.QInt8, op_types_to_quantize=["MatMul", "Gemm"], per_channel=True, extra_options={"MatMulConstBOnly": True})
                    qinfer, qtokens = graph_encoder(quantized, path / "tokenizer.json", config["max_length"])
                    qoutput = qinfer(parity_texts)
                    require(qoutput.shape == expected.shape and np.isfinite(qoutput).all(), "INT8_STRUCTURE_FAILED")
                    parity_results["candidate_int8"] = {"status": "completed", "token_parity": all(np.array_equal(reference_tokens[k], qtokens(parity_texts)[k]) for k in observed_tokens), "max_abs_errors": np.max(np.abs(expected - qoutput), axis=1).tolist(), "cosine_distances": (1 - (expected * qoutput).sum(axis=1)).tolist(), "quantized_ops": ["MatMul", "Gemm"], "weight_type": "QInt8", "per_channel": True, "calibration": "not applicable to dynamic weight quantization"}
                    bundles["candidate_int8"] = str(make_bundle("candidate_int8", quantized, path / "tokenizer.json", parent, documents, config))
                except Exception as error:
                    parity_results["candidate_int8"] = {"status": "failed", "error": type(error).__name__ + ": " + str(error)[:400]}
            del model
        atomic_json(root / "parity.json", parity_results)
        validations, resources = {}, {}
        for method, path in bundles.items():
            bundle = Bundle(path)
            rankings = {q: [d for d, _ in exact_search(bundle.encode([queries[q]["text"]])[0], bundle.matrix, bundle.ids)] for q in split["validation"]}
            validations[method] = {"ndcg10": sum(grade(rankings[q], gold[q])["ndcg10"] for q in split["validation"]) / len(split["validation"]), "queries": len(split["validation"]), "bundle_id": bundle.id}
            atomic_json(root / f"{method}-validation-rankings.json", rankings)
            del bundle
            output = root / f"{method}-resources.json"
            command = [sys.executable, "-m", "hardcase.inference.measure", path, str(root / "timing-queries.json"), str(output)]
            if method != "base_float32":
                command.append(bundles["base_float32"])
            subprocess.run(command, check=True)
            resources[method] = load_json(output)
        parent_quality = selection["candidate"]["ndcg10"]
        eligible = "candidate_int8" in validations and validations["candidate_int8"]["ndcg10"] >= parent_quality - 0.01 and resources["candidate_int8"]["warm_p95_ms"] < config["promotion"]["warm_p95_ms_max"] and resources["candidate_int8"]["peak_rss_mib"] < config["promotion"]["peak_rss_mib_max"]
        variant = "candidate_int8" if eligible and resources["candidate_int8"]["warm_p95_ms"] < resources["candidate_float32"]["warm_p95_ms"] else "candidate_float32"
        frozen = {"state": "serving_variant_selected_before_test", "variant": variant, "bundles": bundles, "validation": validations, "resources": resources, "parity": parity_results, "selection_id": selection["selection_id"], "created_at": utcnow()}
        frozen["export_id"] = digest(frozen)
        atomic_json(root / "selection.json", frozen)
        report.update(variant=variant, export_id=frozen["export_id"], bundles={m: v["bundle_id"] for m, v in validations.items()})


if __name__ == "__main__":
    build()
