import os
import random
import shutil
from pathlib import Path
from hardcase.contracts import atomic_json, digest, file_digest, load_json, require
from .encoder import save_encoder


def save_checkpoint(root, model, tokenizer, optimizer, scheduler, update, cursor, identity):
    import numpy as np
    import torch
    root = Path(root)
    temporary = root.with_name(root.name + ".pending")
    require(not temporary.exists() and not root.exists(), "CHECKPOINT_ALREADY_EXISTS")
    temporary.mkdir(parents=True)
    save_encoder(model, tokenizer, temporary / "encoder")
    torch.save({"optimizer": optimizer.state_dict(), "scheduler": scheduler.state_dict(), "torch_rng": torch.get_rng_state(), "python_rng": random.getstate(), "numpy_rng": np.random.get_state(), "update": update, "cursor": cursor, "identity": identity}, temporary / "trusted-state.pt")
    files = {p.relative_to(temporary).as_posix(): file_digest(p) for p in sorted(temporary.rglob("*")) if p.is_file()}
    manifest = {"identity": identity, "identity_digest": digest(identity), "update": update, "cursor": cursor, "files": files}
    atomic_json(temporary / "manifest.json", manifest)
    temporary.replace(root)
    atomic_json(root.parent / "latest.json", {"path": root.name, "manifest_digest": digest(manifest)})
    return manifest


def load_checkpoint(root, identity, model, optimizer, scheduler):
    import numpy as np
    import torch
    from safetensors.torch import load_file
    root = Path(root)
    manifest = load_json(root / "manifest.json")
    require(manifest["identity_digest"] == digest(identity) and manifest["identity"] == identity, "RESUME_IDENTITY_CHANGED")
    for name, expected in manifest["files"].items():
        require(file_digest(root / name) == expected, "INCOMPLETE_CHECKPOINT")
    model.load_state_dict(load_file(root / "encoder/model.safetensors"))
    # Trusted, hash-validated worker output only. Never exposed as an upload/API.
    state = torch.load(root / "trusted-state.pt", map_location="cpu", weights_only=False)
    require(state["identity"] == identity and state["update"] == manifest["update"], "CHECKPOINT_STATE_MISMATCH")
    optimizer.load_state_dict(state["optimizer"])
    scheduler.load_state_dict(state["scheduler"])
    torch.set_rng_state(state["torch_rng"])
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    return state["update"], state["cursor"]
