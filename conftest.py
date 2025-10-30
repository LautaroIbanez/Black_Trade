"""Pytest configuration: ensure project root is on sys.path for imports."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))


