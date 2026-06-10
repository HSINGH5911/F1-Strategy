import os
import sys

# Ensure the repo root is on sys.path before importing app modules.
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from ui.Sim import main

if __name__ == "__main__":
    main()
