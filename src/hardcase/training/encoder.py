import hashlib
import shutil
import time
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require, utcnow


def download_locked(role):
    from huggingface_hub import snapshot_download
    lock = load_json("requests/model-lock.json")[role]
    location = Path(snapshot_download(lock["repo_id"], revision=lock["revision"], allow_patterns=list(lock["files"]), local_dir=f"models/{role}"))
    for name, expected in lock["files"].items():
        require(file_digest(location / name) == expected, "MODEL_DOWNLOAD_DIGEST_MISMATCH")
    return location


def load_encoder(path):
    from transformers import AutoModel, AutoTokenizer
    model = AutoModel.from_pretrained(path, local_files_only=True, trust_remote_code=False, attn_implementation="eager")
    tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False, use_fast=True)
    return model, tokenizer


def pool(model, batch):
    import torch
    hidden = model(**batch).last_hidden_state
    mask = batch["attention_mask"].unsqueeze(-1).to(hidden.dtype)
    return torch.nn.functional.normalize((hidden * mask).sum(1) / mask.sum(1).clamp(min=1), p=2, dim=1)


def parameter_hashes(model):
    return {n: hashlib.sha256(p.detach().cpu().contiguous().numpy().tobytes()).hexdigest() for n, p in model.state_dict().items()}


def freeze_policy(model):
    require(hasattr(model, "encoder") and len(model.encoder.layer) == 6, "UNSUPPORTED_ARCHITECTURE")
    names = []
    for name, parameter in model.named_parameters():
        parameter.requires_grad_(name.startswith(("encoder.layer.4.", "encoder.layer.5.")))
        if parameter.requires_grad:
            names.append(name)
    require(names and all(any(n.startswith(f"encoder.layer.{i}.") for n in names) for i in (4, 5)), "EMPTY_FREEZE_POLICY")
    return names


def encode(model, tokenizer, texts, max_length, batch_size=16, receipt_path=None, identity=None):
    import numpy as np
    import torch
    require(bool(texts), "EMPTY_ENCODING_INPUT")
    started = utcnow()
    start = time.perf_counter()
    previous = model.training
    model.eval()
    vectors, token_count = [], 0
    with torch.inference_mode():
        for offset in range(0, len(texts), batch_size):
            batch = tokenizer(texts[offset:offset + batch_size], padding=True, truncation=True, max_length=max_length, return_tensors="pt")
            token_count += int(batch["attention_mask"].sum())
            vectors.append(pool(model, batch).cpu().numpy())
    model.train(previous)
    result = np.concatenate(vectors).astype(np.float32)
    require(result.shape == (len(texts), 384) and np.isfinite(result).all(), "INVALID_ENCODER_OUTPUT")
    if receipt_path:
        atomic_json(receipt_path, {"namespace": "actual_inference", "input_digest": digest(texts), "model": identity, "rows": len(texts), "encoded_tokens": token_count, "shape": list(result.shape), "vectors_digest": hashlib.sha256(result.tobytes()).hexdigest(), "seconds": time.perf_counter() - start, "started_at": started, "ended_at": utcnow(), "mode": "fresh"})
    return result


def save_encoder(model, tokenizer, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(destination, safe_serialization=True)
    tokenizer.save_pretrained(destination)
    for name in ("modules.json", "sentence_bert_config.json", "config_sentence_transformers.json", "1_Pooling/config.json"):
        source = Path("models/student") / name
        if source.exists():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    (destination / "2_Normalize").mkdir(exist_ok=True)
