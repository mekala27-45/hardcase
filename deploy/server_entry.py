"""Reviewed production entry to activate only with a verified runtime request."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from hardcase.api.server import app
