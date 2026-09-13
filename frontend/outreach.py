"""
frontend/outreach.py
Forwards to outreach_layer.outreach for frontend import compatibility.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from outreach_layer.outreach import generate_outreach, match_segment
