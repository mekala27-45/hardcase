import json
import os
import sys
from pathlib import Path
sys.path.insert(0, "src")
from hardcase.contracts import atomic_json, load_json, digest


def existing(path, default=None):
    path = Path(path)
    return load_json(path) if path.exists() else default


def build():
    preparation = existing("evidence/preparation/prepare.json", {})
    source = existing("evidence/preparation/source.json", {})
    selection = existing("evidence/training/selection.json", {})
    evaluation = existing("evidence/evaluation/report.json", {})
    release = existing("evidence/release/decision.json", {})
    arms, steps = [], []
    for arm in ["uniform_contrastive", "hard_contrastive", "hard_distilled"]:
        run = existing(f"evidence/training/{arm}/run.json", {})
        arms.append({"arm": arm, "status": run.get("status", "not_started"), "updates": run.get("actual_updates"), "selected_update": run.get("selected", {}).get("update")})
        path = Path(f"evidence/training/{arm}/steps.jsonl")
        if path.exists():
            steps.extend(json.loads(line) for line in path.read_text().splitlines())
    result = {"completion_state": "Experiment in progress", "api_url": os.getenv("PUBLIC_API_URL", ""), "default_model": release.get("default_model"), "training": {"arms": arms, "steps": steps}, "evaluation": evaluation, "release": release, "data": {"inventory": [{"item": key, "observed": value, "source": "evidence/preparation/source.json"} for key, value in source.get("observed", {}).items()], "audit": existing("evidence/preparation/mining-audit.json", [])}, "source_digests": {"preparation": digest(preparation), "selection": digest(selection), "evaluation": digest(evaluation), "release": digest(release)}}
    atomic_json("site/public/evidence.json", result)


if __name__ == "__main__":
    build()
