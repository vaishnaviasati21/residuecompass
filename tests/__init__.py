import sys
from pathlib import Path

# Automatically ensure 'src' is available in Python path
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
