"""
data_manager.py
Data handling and persistence layer for the Sports Lot Optimiser project.
"""

from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

# Directory relative to this module
BASE_DIR = Path(__file__).parent.resolve()
DATA_DIR = BASE_DIR / "data"

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


def _get_target_paths(filename: str) -> List[Path]:
    """Returns all existing/intended target paths for a CSV file (data/ and project root)."""
    paths = []
    # Primary data directory path
    data_path = DATA_DIR / filename
    paths.append(data_path)
    
    # Root directory path
    root_path = BASE_DIR / filename
    if root_path != data_path:
        paths.append(root_path)
    return paths


def _find_read_path(filename: str) -> Path:
    """Finds the path to read a CSV file from, checking data/ first then project root."""
    data_path = DATA_DIR / filename
    if data_path.exists():
        return data_path
    root_path = BASE_DIR / filename
    if root_path.exists():
        return root_path
    raise FileNotFoundError(
        f"'{filename}' was not found in '{DATA_DIR}' or '{BASE_DIR}'. "
        "Please run generate_dataset.py first."
    )


def load_slots() -> pd.DataFrame:
    """
    Loads and returns slots.csv as a pandas DataFrame.
    """
    file_path = _find_read_path("slots.csv")
    return pd.read_csv(file_path)


def load_segments() -> pd.DataFrame:
    """
    Loads and returns customer_segments.csv as a pandas DataFrame.
    """
    file_path = _find_read_path("customer_segments.csv")
    return pd.read_csv(file_path)


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

    # Save to all target locations (data/ and root) to keep them synchronized
    target_paths = _get_target_paths("slots.csv")
    for path in target_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        slots_df.to_csv(path, index=False)


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

    # Append to all target locations (data/ and root)
    target_paths = _get_target_paths("booking_log.csv")
    for path in target_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_header = not path.exists() or path.stat().st_size == 0
        new_row_df.to_csv(path, mode="a", header=write_header, index=False)
