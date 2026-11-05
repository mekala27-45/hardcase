import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path("artifacts/setup")
root.mkdir(parents=True, exist_ok=True)
status = "completed" if int(sys.argv[1]) == 0 else "failed"
(root / "terminal.json").write_text(json.dumps({"status": status, "exit_code": int(sys.argv[1]), "source_commit": os.getenv("GITHUB_SHA"), "run_id": os.getenv("GITHUB_RUN_ID"), "observed_at": datetime.now(timezone.utc).isoformat()}, sort_keys=True) + "\n")
