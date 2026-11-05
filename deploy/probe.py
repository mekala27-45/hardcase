"""Bounded real-model setup probe. No test labels are opened."""
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hardcase.contracts import Stage, atomic_json, digest, file_digest, load_json, require, utcnow


def main():
    root = Path("artifacts/setup")
    root.mkdir(parents=True, exist_ok=True)
    request = load_json("requests/setup.json")
    require(request == {"schema_version": 1, "action": "setup", "experiment": "requests/experiment.json", "max_updates": 10, "runner": "ubuntu-24.04", "output": "artifacts/setup"}, "INVALID_SETUP_REQUEST")
    config = load_json(request["experiment"])
    with Stage(root, "probe", {"request": request, "preregistration": digest(config)}) as report:
        import numpy as np
        import torch
        import onnxruntime as ort
        from huggingface_hub import HfApi, snapshot_download
        from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(2)
        torch.manual_seed(config["seed"])
        torch.use_deterministic_algorithms(True)
        report["environment"] = {"python": platform.python_version(), "platform": platform.platform(), "processor": platform.processor(), "threads": torch.get_num_threads(), "cpu_count": os.cpu_count(), "packages": {p: importlib.metadata.version(p) for p in ["torch", "transformers", "sentence-transformers", "onnx", "onnxruntime", "numpy", "tokenizers", "safetensors", "huggingface-hub"]}}
        lock = {}
        for role in ("student", "teacher"):
            name = config[role]
            revision = HfApi().model_info(name).sha
            require(len(revision) == 40, "MODEL_REVISION_NOT_FULL")
            location = Path(snapshot_download(name, revision=revision, allow_patterns=["*.json", "*.txt", "*.safetensors", "README.md", "LICENSE*", "1_Pooling/*"], local_dir=f"models/{role}"))
            lock[role] = {"repo_id": name, "revision": revision, "files": {p.relative_to(location).as_posix(): file_digest(p) for p in sorted(location.rglob("*")) if p.is_file() and ".cache" not in p.parts}}
        atomic_json(root / "model-lock.json", lock)
        tokenizer = AutoTokenizer.from_pretrained("models/student", local_files_only=True, use_fast=True, trust_remote_code=False)
        model = AutoModel.from_pretrained("models/student", local_files_only=True, trust_remote_code=False, attn_implementation="eager")
        require(len(model.encoder.layer) == 6, "STUDENT_ARCHITECTURE")
        names = []
        for name, parameter in model.named_parameters():
            parameter.requires_grad_(name.startswith(("encoder.layer.4.", "encoder.layer.5.")))
            if parameter.requires_grad:
                names.append(name)
        before = {n: p.detach().clone() for n, p in model.named_parameters()}
        report["trainable_names"] = names
        report["trainable_parameters"] = sum(p.numel() for p in model.parameters() if p.requires_grad)
        report["total_parameters"] = sum(p.numel() for p in model.parameters())
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=config["learning_rate"], weight_decay=config["weight_decay"])
        authored = ["An assay measures protein expression.", "A protein assay measures expression in cells.", "The observations describe stellar motion.", "The control sample has no measured expression.", "A trial used randomized allocation.", "The instrument measures atmospheric pressure."]
        batch = tokenizer(authored, padding="max_length", truncation=True, max_length=config["max_length"], return_tensors="pt")

        def encode(batch):
            tokens = model(**batch).last_hidden_state
            mask = batch["attention_mask"].unsqueeze(-1)
            return torch.nn.functional.normalize((tokens * mask).sum(1) / mask.sum(1).clamp(min=1), p=2, dim=1)

        updates = []
        model.train()
        for step in range(10):
            start = time.perf_counter()
            optimizer.zero_grad()
            for _ in range(8):
                vectors = encode(batch)
                logits = vectors[0] @ vectors[1:].T / config["student_temperature"]
                loss = torch.logsumexp(logits, 0) - logits[0]
                (loss / 8).backward()
            norm = torch.nn.utils.clip_grad_norm_(model.parameters(), config["gradient_norm_cap"])
            require(torch.isfinite(norm).item() and norm.item() > 0, "INVALID_GRADIENT")
            optimizer.step()
            updates.append({"update": step + 1, "seconds": time.perf_counter() - start, "gradient_norm": float(norm), "loss": float(loss.detach())})
        changed = {n: float((p.detach() - before[n]).abs().max()) for n, p in model.named_parameters()}
        require(all(changed[n] == 0 for n, p in model.named_parameters() if not p.requires_grad), "FROZEN_TENSOR_CHANGED")
        require(any(changed[n] > 0 for n in names), "NO_PARAMETER_CHANGE")
        report["actual_training_probe"] = {"namespace": "actual_training", "fixture": "authored setup texts, not benchmark training", "updates": updates, "changed_parameters": changed, "projected_three_arm_optimization_seconds": float(np.median([x["seconds"] for x in updates[1:]])) * 360}
        teacher = AutoModelForSequenceClassification.from_pretrained("models/teacher", local_files_only=True, trust_remote_code=False).eval()
        teacher_tokenizer = AutoTokenizer.from_pretrained("models/teacher", local_files_only=True, trust_remote_code=False)
        teacher_batch = teacher_tokenizer([authored[0]] * 5, authored[1:], padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            scores = teacher(**teacher_batch).logits.flatten().tolist()
        report["teacher_probe"] = {"namespace": "teacher_supervision", "pair_count": len(scores), "scores": scores, "pair_digest": digest(authored)}
        del teacher

        class Pooled(torch.nn.Module):
            def __init__(self, encoder):
                super().__init__()
                self.encoder = encoder

            def forward(self, input_ids, attention_mask, token_type_ids):
                output = self.encoder(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids).last_hidden_state
                mask = attention_mask.unsqueeze(-1).to(output.dtype)
                return torch.nn.functional.normalize((output * mask).sum(1) / mask.sum(1).clamp(min=1), p=2, dim=1)

        wrapper = Pooled(model.eval()).eval()
        inputs = tuple(batch[k] for k in ("input_ids", "attention_mask", "token_type_ids"))
        onnx_path = root / "probe.onnx"
        torch.onnx.export(wrapper, inputs, str(onnx_path), input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["embeddings"], dynamic_axes={k: {0: "batch", 1: "sequence"} for k in ("input_ids", "attention_mask", "token_type_ids")} | {"embeddings": {0: "batch"}}, opset_version=18, dynamo=False)
        session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        observed = session.run(None, {x.name: batch[x.name].numpy() for x in session.get_inputs()})[0]
        with torch.no_grad():
            expected = wrapper(*inputs).numpy()
        absolute = float(np.max(np.abs(expected - observed)))
        cosine = float(np.max(1 - np.sum(expected * observed, axis=1)))
        require(absolute <= config["export"]["max_abs_error"], "EXPORT_ABSOLUTE_PARITY")
        require(cosine <= config["export"]["max_cosine_distance"], "EXPORT_COSINE_PARITY")
        report["export_probe"] = {"namespace": "export_parity", "max_abs_error": absolute, "max_cosine_distance": cosine, "graph_sha256": file_digest(onnx_path), "graph_bytes": onnx_path.stat().st_size, "shape": list(observed.shape), "exporter": "torchscript dynamo=False", "opset": 18}
        report["model_lock_digest"] = digest(lock)
        atomic_json(root / "environment.json", report["environment"])
        (root / "resolved-packages.txt").write_text(subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True), encoding="utf-8")


if __name__ == "__main__":
    main()
