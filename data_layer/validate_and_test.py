"""
validate_and_test.py
Validates dataset quality and tests data_layer functions.
Part of Data Layer (Person A).
"""

import sys
from pathlib import Path

# Add project root to sys.path so 'data_layer' package is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from datetime import datetime
import pandas as pd
from data_layer import load_slots, load_segments, update_slot_status, append_to_log


def validate_and_test():
    print("=" * 60)
    print("1. VALIDATING DATA QUALITY IN DATA_LAYER")
    print("=" * 60)
    slots_df = load_slots()
    segments_df = load_segments()

    # 1. Column schema check
    expected_slot_cols = [
        "slot_id", "turf_name", "sport", "date", "day_of_week",
        "time_slot", "lead_time_hrs", "base_price", "cost_to_operate",
        "historical_fill_rate", "status", "tags"
    ]
    assert list(slots_df.columns) == expected_slot_cols, f"Mismatch in slots.csv columns: {list(slots_df.columns)}"
    print("[PASS] slots.csv column schema matches exactly.")

    # 2. No duplicate slot_id
    assert slots_df["slot_id"].nunique() == len(slots_df), "Found duplicate slot_ids!"
    print(f"[PASS] slot_id is strictly unique (Total: {len(slots_df)} slots).")

    # 3. No missing values
    assert slots_df.isnull().sum().sum() == 0, "Found null/missing values in slots.csv!"
    print("[PASS] No missing values in slots.csv.")

    # 4. historical_fill_rate between 0 and 1
    assert (slots_df["historical_fill_rate"] >= 0.0).all() and (slots_df["historical_fill_rate"] <= 1.0).all(), \
        "historical_fill_rate out of [0, 1] range!"
    print("[PASS] historical_fill_rate strictly bounded between 0.0 and 1.0.")

    # 5. cost_to_operate < base_price
    assert (slots_df["cost_to_operate"] < slots_df["base_price"]).all(), \
        "cost_to_operate must always be strictly less than base_price!"
    print("[PASS] cost_to_operate < base_price for 100% of slots.")

    # 6. status valid
    assert set(slots_df["status"].unique()).issubset({"vacant", "booked"}), \
        "Invalid status values found!"
    print(f"[PASS] Status values strictly valid: {set(slots_df['status'].unique())}.")

    # 7. Dates and day_of_week
    for _, row in slots_df.iterrows():
        dt = datetime.strptime(row["date"], "%Y-%m-%d")
        expected_day = dt.strftime("%A")
        assert row["day_of_week"] == expected_day, f"Day mismatch for {row['date']}: {row['day_of_week']} vs {expected_day}"
    print("[PASS] All dates correctly correspond to day_of_week.")

    # 8. Low fill rate for weekday afternoons
    afternoon_slots = {"12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"}
    evening_slots = {"17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"}
    
    wk_aft_mask = (~slots_df["day_of_week"].isin(["Saturday", "Sunday"])) & (slots_df["time_slot"].isin(afternoon_slots))
    wk_aft_avg = slots_df.loc[wk_aft_mask, "historical_fill_rate"].mean()
    
    ev_wk_mask = (slots_df["day_of_week"].isin(["Saturday", "Sunday"])) | (slots_df["time_slot"].isin(evening_slots))
    ev_wk_avg = slots_df.loc[ev_wk_mask, "historical_fill_rate"].mean()
    
    assert wk_aft_avg < ev_wk_avg, "Weekday afternoon fill rate must be significantly lower than evening/weekend fill rate!"
    print(f"[PASS] Weekday afternoon avg fill rate ({wk_aft_avg:.3f}) is visibly lower than evening/weekend ({ev_wk_avg:.3f}).")

    # 9. Required columns in customer_segments.csv
    expected_segment_cols = [
        "segment_id", "segment_name", "sport_pref", "preferred_time_band", "price_sensitivity", "size"
    ]
    assert list(segments_df.columns) == expected_segment_cols, f"Mismatch in customer_segments.csv columns: {list(segments_df.columns)}"
    assert segments_df["segment_id"].nunique() == len(segments_df), "Duplicate segment_ids found!"
    assert set(segments_df["price_sensitivity"].unique()).issubset({"low", "medium", "high"}), "Invalid price_sensitivity!"
    print(f"[PASS] customer_segments.csv schema valid (Total: {len(segments_df)} segments).")

    print("\n" + "=" * 60)
    print("2. TESTING DATA_LAYER FUNCTIONS")
    print("=" * 60)
    
    # Find a vacant slot
    vacant_slots = slots_df[slots_df["status"] == "vacant"]
    assert len(vacant_slots) > 0, "No vacant slots found!"
    target_slot = vacant_slots.iloc[0]
    target_id = target_slot["slot_id"]
    print(f"1. Found vacant slot: {target_id} ({target_slot['turf_name']}, {target_slot['sport']}, {target_slot['date']} {target_slot['time_slot']})")

    # Change slot from vacant to booked
    print(f"2. Calling update_slot_status('{target_id}', 'booked')...")
    update_slot_status(target_id, "booked")
    
    reloaded_slots = load_slots()
    updated_status = reloaded_slots.loc[reloaded_slots["slot_id"] == target_id, "status"].values[0]
    assert updated_status == "booked", f"Expected booked, got {updated_status}"
    print(f"[PASS] Slot {target_id} status successfully updated to: {updated_status}")

    # Append one example booking log entry
    sample_log = {
        "slot_id": target_id,
        "decision": "notify_small_discount",
        "discount_pct": 15.0,
        "reasoning": ["Low historical fill rate (0.24)", "Short lead time (6h)", "Ample margin room (45%)"],
        "segment_notified": "SEG_04",
        "source": "rule_based_fallback",
        "timestamp": datetime.now().isoformat()
    }
    print("3. Calling append_to_log() with sample decision...")
    append_to_log(sample_log)
    
    # Read booking_log.csv
    log_path = Path(__file__).parent / "booking_log.csv"
    log_df = pd.read_csv(log_path)
    assert len(log_df) >= 1, "booking_log.csv should contain at least 1 row!"
    last_row = log_df.iloc[-1]
    assert last_row["slot_id"] == target_id, f"Expected {target_id}, got {last_row['slot_id']}"
    assert last_row["decision"] == "notify_small_discount"
    print(f"[PASS] booking_log.csv verified with {len(log_df)} row(s).")

    # Reset slot back to vacant so data stays clean
    update_slot_status(target_id, "vacant")
    print(f"[PASS] Reset slot {target_id} back to 'vacant'.")

    print("\n" + "=" * 60)
    print("ALL VALIDATION CHECKS & TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    validate_and_test()
