# Test package for Agentic Broadcast Assistant
import os
import sys

# Ensure auto-direction root directory is in sys.path
_parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)
