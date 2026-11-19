"""
AeroTouch Root Entrypoint
Allows launching AeroTouch directly via:
    python main.py
"""

import sys
import os

# Ensure project root is in sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.main import main

if __name__ == "__main__":
    main()
