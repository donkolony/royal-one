"""Make `app` importable when a script is run as `python scripts/<name>.py` from the backend folder."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
