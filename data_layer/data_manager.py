"""
data_manager.py
Data handling and persistence layer for the Sports Lot Optimiser project.
Part of the Data Layer (Person A).
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd

# Directory where this file and the CSVs reside
DATA_DIR = Path(__file__).parent.resolve()
SLOTS_FILE = DATA_DIR / "slots.csv"
SEGMENTS_FILE = DATA_DIR / "customer_segments.csv"
BOOKING_LOG_FILE = DATA_DIR / "booking_log.csv"

VALID_STATUSES = {"vacant", "booked"}
LOG_COLUMNS = [
    "slot_id",
    "decision",
    "discount_pct",
    "reasoning",
    "segment_notified",
    "source",
    "timestamp",
]


def load_slots() -> pd.DataFrame:
    """
    Loads and returns slots.csv as a pandas DataFrame.
    """
    if not SLOTS_FILE.exists():
        raise FileNotFoundError(
            f"slots.csv not found at {SLOTS_FILE}. Please run generate_dataset.py first."
        )
    return pd.read_csv(SLOTS_FILE)


def load_segments() -> pd.DataFrame:
    """
    Loads and returns customer_segments.csv as a pandas DataFrame.
    """
    if not SEGMENTS_FILE.exists():
        raise FileNotFoundError(
            f"customer_segments.csv not found at {SEGMENTS_FILE}. Please run generate_dataset.py first."
        )
    return pd.read_csv(SEGMENTS_FILE)


def update_slot_status(slot_id: str, new_status: str) -> None:
    """
    Updates the status of the specified slot in slots.csv.

    Args:
        slot_id: The unique ID of the slot (e.g., 'S1001').
        new_status: The new status string, must be either 'vacant' or 'booked'.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Allowed values are: {sorted(list(VALID_STATUSES))}"
        )

    slots_df = load_slots()

    slot_mask = slots_df["slot_id"] == slot_id
    if not slot_mask.any():
        raise ValueError(f"Slot ID '{slot_id}' not found in slots.csv")

    slots_df.loc[slot_mask, "status"] = new_status
    slots_df.to_csv(SLOTS_FILE, index=False)


def append_to_log(log_row_dict: Dict[str, Any]) -> None:
    """
    Appends a new decision/booking entry to booking_log.csv.

    Args:
        log_row_dict: Dictionary containing log columns:
            slot_id, decision, discount_pct, reasoning,
            segment_notified, source, timestamp
    """
    formatted_dict = dict(log_row_dict)
    
    # If reasoning is passed as a list (e.g. from LLM bullets), format to a single readable string
    if isinstance(formatted_dict.get("reasoning"), list):
        formatted_dict["reasoning"] = "; ".join(str(item) for item in formatted_dict["reasoning"])

    # Ensure all expected columns exist
    row_data = {col: formatted_dict.get(col, "") for col in LOG_COLUMNS}
    new_row_df = pd.DataFrame([row_data])

    write_header = not BOOKING_LOG_FILE.exists() or BOOKING_LOG_FILE.stat().st_size == 0
    new_row_df.to_csv(BOOKING_LOG_FILE, mode="a", header=write_header, index=False)
