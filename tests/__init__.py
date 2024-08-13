import os
import sys
from pathlib import Path


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../app")))

DATA_DIR = Path(__file__).resolve().parent / "data"
