"""
integration.py
Bridge module connecting the Streamlit Frontend to the Data Layer,
Reasoning Engine (LLM), and Outreach Layer.
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple
import pandas as pd

# Add project root to sys.path so all layer modules can be resolved
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also add if running from frontend folder
PARENT_DIR = PROJECT_ROOT.parent if PROJECT_ROOT.name == "frontend" else PROJECT_ROOT
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from data_layer.data_manager import (
    load_slots as dl_load_slots,
    load_segments as dl_load_segments,
    update_slot_status as dl_update_slot_status,
    append_to_log as dl_append_to_log,
    SLOTS_FILE,
    BOOKING_LOG_FILE,
    LOG_COLUMNS,
)
from engine.reasoning_llm import evaluate_slot as engine_evaluate_slot
from outreach_layer.outreach import generate_outreach as engine_generate_outreach

DEMO_SLOTS = [
    {
        "slot_id": "S101-DEMO",
        "turf_name": "Apex Arena",
        "sport": "Football",
        "date": "2026-09-15",
        "day_of_week": "Tuesday",
        "time_slot": "14:00-15:00",
        "lead_time_hrs": 3.0,
        "base_price": 1200.0,
        "cost_to_operate": 450.0,
        "historical_fill_rate": 0.22,
        "status": "vacant",
        "tags": "weekday_afternoon,students",
    },
    {
        "slot_id": "S102-DEMO",
        "turf_name": "Apex Arena",
        "sport": "Football",
        "date": "2026-09-16",
        "day_of_week": "Wednesday",
        "time_slot": "16:00-17:00",
        "lead_time_hrs": 20.0,
        "base_price": 1100.0,
        "cost_to_operate": 450.0,
        "historical_fill_rate": 0.45,
        "status": "vacant",
        "tags": "afternoon,casual",
    },
    {
        "slot_id": "S103-DEMO",
        "turf_name": "Apex Arena",
        "sport": "Football",
        "date": "2026-09-19",
        "day_of_week": "Saturday",
        "time_slot": "19:00-20:00",
        "lead_time_hrs": 8.0,
        "base_price": 1300.0,
        "cost_to_operate": 450.0,
        "historical_fill_rate": 0.90,
        "status": "vacant",
        "tags": "prime_time,weekend",
    },
]


def _ensure_demo_slots_in_csv():
    """Ensures the 3 sidebar demo slots exist in slots.csv."""
    try:
        df = dl_load_slots()
        existing_ids = set(df["slot_id"].tolist())
        to_add = [s for s in DEMO_SLOTS if s["slot_id"] not in existing_ids]
        if to_add:
            demo_df = pd.DataFrame(to_add)
            combined_df = pd.concat([demo_df, df], ignore_index=True)
            combined_df.to_csv(SLOTS_FILE, index=False)
    except Exception as e:
        print(f"Warning ensuring demo slots: {e}")


def load_slots() -> pd.DataFrame:
    """Loads slots DataFrame and guarantees demo slots are present."""
    _ensure_demo_slots_in_csv()
    return dl_load_slots()


def load_segments() -> pd.DataFrame:
    """Loads customer segments DataFrame."""
    return dl_load_segments()


def load_booking_log() -> pd.DataFrame:
    """Loads booking history log DataFrame."""
    if not BOOKING_LOG_FILE.exists() or BOOKING_LOG_FILE.stat().st_size == 0:
        return pd.DataFrame(columns=LOG_COLUMNS)
    try:
        return pd.read_csv(BOOKING_LOG_FILE)
    except Exception:
        return pd.DataFrame(columns=LOG_COLUMNS)


def evaluate_slot(slot: Dict[str, Any]) -> Dict[str, Any]:
    """Invokes LLM reasoning agent with rule-based fallback."""
    return engine_evaluate_slot(slot)


def generate_outreach(slot: Dict[str, Any], decision_result: Dict[str, Any], segments_df: pd.DataFrame) -> Dict[str, str]:
    """Invokes outreach matching and message generation."""
    return engine_generate_outreach(slot, decision_result, segments_df)


def book_slot(
    slot_id: str,
    eval_data: Dict[str, Any],
    segment_notified: str = "Direct",
) -> Tuple[bool, str]:
    """
    Confirms booking for a slot:
    1. Updates slot status to 'booked' in slots.csv
    2. Logs the booking to booking_log.csv
    """
    try:
        # Update slot status
        dl_update_slot_status(slot_id, "booked")

        # Prepare log entry
        log_entry = {
            "slot_id": slot_id,
            "decision": eval_data.get("decision", "no_action"),
            "discount_pct": eval_data.get("discount_pct", 0.0),
            "reasoning": eval_data.get("reasoning", []),
            "segment_notified": segment_notified,
            "source": eval_data.get("source", "llm"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        dl_append_to_log(log_entry)
        return True, f"Slot {slot_id} successfully booked and recorded!"
    except Exception as e:
        return False, f"Failed to book slot {slot_id}: {str(e)}"


def reset_demo_data():
    """Resets the dataset to clean initial state with demo slots set to vacant."""
    try:
        from data_layer.generate_dataset import main as gen_main
        gen_main()
    except Exception:
        pass
    _ensure_demo_slots_in_csv()
    # Ensure demo slots are vacant
    try:
        df = dl_load_slots()
        demo_ids = [s["slot_id"] for s in DEMO_SLOTS]
        df.loc[df["slot_id"].isin(demo_ids), "status"] = "vacant"
        df.to_csv(SLOTS_FILE, index=False)
    except Exception as e:
        print(f"Error resetting demo slots: {e}")
