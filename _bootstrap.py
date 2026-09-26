# _bootstrap.py — adds the project root to sys.path so that
# submodules inside models/, utils/, pages/ can import config, database, etc.
# Import this as the very first line of any submodule file.

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)