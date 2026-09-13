"""
test_data_layer.py
Tests the data_layer package functions.
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'data_layer' package is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime
from data_layer import load_slots, load_segments, update_slot_status, append_to_log
import pandas as pd


def test_layer():
    slots = load_slots()
    segments = load_segments()
    print(f"[PASS] Loaded {len(slots)} slots and {len(segments)} segments from data_layer.")

    assert len(slots) == 180
    assert len(segments) == 7

    # Find a vacant slot
    vacant = slots[slots["status"] == "vacant"].iloc[0]
    slot_id = vacant["slot_id"]
    print(f"[INFO] Testing with vacant slot: {slot_id}")

    # Update slot
    update_slot_status(slot_id, "booked")
    reloaded = load_slots()
    assert reloaded.loc[reloaded["slot_id"] == slot_id, "status"].values[0] == "booked"
    print(f"[PASS] Successfully updated slot {slot_id} to booked.")

    # Append to log
    sample_log = {
        "slot_id": slot_id,
        "decision": "notify_small_discount",
        "discount_pct": 15.0,
        "reasoning": ["Low historical fill rate", "Good margin room"],
        "segment_notified": "SEG_04",
        "source": "rule_based_fallback",
        "timestamp": datetime.now().isoformat()
    }
    append_to_log(sample_log)
    print(f"[PASS] Successfully appended log entry for {slot_id}.")

    # Reset slot back to vacant so data stays clean
    update_slot_status(slot_id, "vacant")
    print("[PASS] Cleaned up test slot status back to vacant.")

    print("\nALL DATA LAYER TESTS PASSED!")


if __name__ == "__main__":
    test_layer()
