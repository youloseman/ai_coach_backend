import sys
from pathlib import Path


# Ensure project root is on sys.path so that modules like `coach` and
# `training_zones` can be imported when running tests.
ROOT_DIR = Path(__file__).resolve().parents[1]
root_str = str(ROOT_DIR)

if root_str not in sys.path:
    sys.path.insert(0, root_str)


