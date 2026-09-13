"""
data_layer package
Exposes data handling and persistence utilities for the Sports Lot Optimiser.
"""

from .data_manager import (
    load_slots,
    load_segments,
    update_slot_status,
    append_to_log,
)

__all__ = [
    "load_slots",
    "load_segments",
    "update_slot_status",
    "append_to_log",
]
