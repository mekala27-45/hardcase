"""Vercel entry point for the immutable ONNX runtime."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'src'))
from hardcase.api.server import app
