"""Make the Index generator (index/pbindex, not part of the wheel) importable."""

import sys
from pathlib import Path

INDEX_DIR = Path(__file__).resolve().parents[2] / "index"
if str(INDEX_DIR) not in sys.path:
    sys.path.insert(0, str(INDEX_DIR))
