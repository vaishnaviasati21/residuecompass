import json
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parents[2] / "seed"


def load_seed(name: str):
    return json.loads((SEED_DIR / f"{name}.json").read_text(encoding="utf-8"))