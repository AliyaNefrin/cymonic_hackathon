
from typing import Dict, Any, Optional
import pandas as pd


def _parse_hour(time_str: str) -> int:
    """Extracts starting hour from '14:00' or '14:00-15:00' format."""
    try:
        start_part = time_str.split("-")[0].strip()
        return int(start_part.split(":")[0])
    except Exception:
        return 12  # safe default


def _time_falls_in_band(slot_time: str, band_time: str) -> bool:
    """
    Checks if a slot (e.g., '14:00-15:00') starts within a band (e.g., '12:00-17:00').
    """
    try:
        slot_start = _parse_hour(slot_time)
        band_parts = band_time.split("-")
        band_start = int(band_parts[0].strip().split(":")[0])
        band_end = int(band_parts[1].strip().split(":")[0])
        return band_start <= slot_start < band_end
    except Exception:
        return True


def match_segment(
    slot: Dict[str, Any],
    segments_df: pd.DataFrame,
    discount_pct: float = 0.0
) -> Optional[Dict[str, Any]]:
    """
    Finds the optimal customer segment for a given slot.
    Prioritizes:
      1. Sport match
      2. Time band overlap
      3. Price sensitivity alignment with discount level
      4. Segment reach (size)
    """
    if segments_df is None or segments_df.empty:
        return {
            "segment_id": "SEG_DEFAULT",
            "segment_name": f"Local {slot.get('sport', 'Sports')} Community",
            "sport_pref": slot.get("sport", "General"),
            "preferred_time_band": "Any",
            "price_sensitivity": "medium",
            "size": 50
        }

    # 1. Match sport
    sport_matches = segments_df[
        segments_df["sport_pref"].astype(str).str.lower() == str(slot.get("sport", "")).lower()
    ]
    if sport_matches.empty:
        sport_matches = segments_df

    # 2. Match time band
    slot_time = str(slot.get("time_slot", ""))
    time_matches = sport_matches[
        sport_matches["preferred_time_band"].apply(lambda band: _time_falls_in_band(slot_time, band))
    ]

    candidates = time_matches if not time_matches.empty else sport_matches

    # 3. Score candidates by discount alignment
    # High discount (>=20%) -> prefer high sensitivity
    # Low/No discount (0-10%) -> prefer low/medium sensitivity
    target_sensitivity = "high" if discount_pct >= 20.0 else ("medium" if discount_pct > 0 else "low")
    
    scored_candidates = candidates.copy()
    scored_candidates["pref_score"] = scored_candidates["price_sensitivity"].apply(
        lambda s: 2 if str(s).lower() == target_sensitivity else 1
    )

    # 4. Sort by score, then audience size descending
    sorted_candidates = scored_candidates.sort_values(
        by=["pref_score", "size"], ascending=[False, False]
    )

    return sorted_candidates.iloc[0].to_dict()


def generate_outreach(
    slot: Dict[str, Any],
    decision_result: Dict[str, Any],
    segments_df: pd.DataFrame
) -> Dict[str, str]:
    """
    Person C Function Contract:
    Takes slot details and Person B's decision, matches customer segment,
    and formats outreach message.

    Returns:
        {
            "matched_segment": str,
            "message": str
        }
    """
    decision = decision_result.get("decision", "no_action")
    discount_pct = float(decision_result.get("discount_pct", 0.0))

    # Case 1: No action needed (slot will fill naturally)
    if decision == "no_action":
        return {
            "matched_segment": "None (No Action)",
            "message": "⏸️ **No Outreach Dispatched**\n\nThe agent determined this slot has high organic demand. Preserving full margin without discounts."
        }

    # Match best audience segment
    segment = match_segment(slot, segments_df, discount_pct=discount_pct)
    segment_name = segment.get("segment_name", "Valued Players")
    segment_size = segment.get("size", 0)

    # Price math
    base_price = float(slot.get("base_price", 1000.0))
    discounted_price = round(base_price * (1.0 - discount_pct / 100.0))
    savings = round(base_price - discounted_price)

    sport = slot.get("sport", "Turf")
    turf_name = slot.get("turf_name", "Main Turf")
    day = slot.get("day_of_week", "Today")
    date = slot.get("date", "")
    time_slot = slot.get("time_slot", "")
    lead_time = slot.get("lead_time_hrs", 0)

    # Sport emojis
    sport_emojis = {
        "football": "⚽",
        "box cricket": "🏏",
        "cricket": "🏏",
        "badminton": "🏸",
        "tennis": "🎾",
        "basketball": "🏀"
    }
    emoji = sport_emojis.get(sport.lower(), "🏆")

    # Format message based on decision type
    if decision == "notify_large_discount":
        urgency_hook = f"🔥 **FLASH FLASH DEAL — {int(discount_pct)}% OFF TODAY!**"
        price_line = f"💰 **Price:** ~₹{int(base_price)}~ ➡️ **₹{discounted_price}** (Save ₹{savings}!)"
        cta = f"⚡ *Only 1 slot left for this afternoon! Tap below to book before it's gone.*"
    elif decision == "notify_small_discount":
        urgency_hook = f"⚡ **Exclusive Member Discount — {int(discount_pct)}% OFF**"
        price_line = f"💰 **Price:** ~₹{int(base_price)}~ ➡️ **₹{discounted_price}** (Save ₹{savings})"
        cta = f"📲 *Grab this slot now and get your squad together!*"
    else:  # notify_only
        urgency_hook = f"📢 **Turf Slot Alert: Now Available**"
        price_line = f"💰 **Rate:** ₹{int(base_price)}"
        cta = f"👉 *Reserve your slot early to secure the pitch.*"

    message = (
        f"{urgency_hook}\n\n"
        f"Hey **{segment_name}** {emoji}\n\n"
        f"A prime {sport} slot just opened up at **{turf_name}**!\n\n"
        f"📅 **Date:** {day}, {date}\n"
        f"⏰ **Time:** {time_slot} (Starting in {lead_time} hrs)\n"
        f"{price_line}\n\n"
        f"{cta}\n\n"
        f"🔗 [Click Here to Instant-Book]\n"
        f"*(Targeting: {segment_name} • {segment_size} members notified)*"
    )

    return {
        "matched_segment": segment_name,
        "message": message
    }


# =====================================================================
# STANDALONE TEST HARNESS
# Run this file directly (`python outreach.py`) to test your code!
# =====================================================================
if __name__ == "__main__":
    import sys
    import os

    # Ensure UTF-8 output encoding for Windows terminal
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # Ensure project root is in sys.path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print("--- TESTING OUTREACH LAYER WITH REAL DATA LAYER ---\n")

    try:
        from data_layer.data_manager import load_segments, load_slots
        live_segments = load_segments()
        live_slots = load_slots()
        print(f"Loaded {len(live_segments)} real segments and {len(live_slots)} slots from data_layer.\n")
        vacant_slots = live_slots[live_slots["status"] == "vacant"]
        sample_slot = vacant_slots.iloc[0].to_dict()
    except Exception as e:
        print(f"Could not load live data: {e}")
        live_segments = pd.DataFrame()
        sample_slot = {"slot_id": "S1001", "turf_name": "Apex Arena", "sport": "Football", "base_price": 1000.0}

    # 1. Test Case A: Large discount decision
    decision_a = {
        "decision": "notify_large_discount",
        "discount_pct": 20.0,
        "confidence": "high",
        "reasoning": ["Low fill rate", "Short lead time"],
        "source": "llm"
    }

    result_a = generate_outreach(sample_slot, decision_a, live_segments)
    print("=== TEST CASE A: Large Discount on Real Slot ===")
    print(f"Slot: {sample_slot.get('slot_id')} ({sample_slot.get('turf_name')} - {sample_slot.get('sport')})")
    print(f"Matched Segment: {result_a['matched_segment']}")
    print("Rendered Message:\n" + result_a["message"])
    print("\n" + "="*50 + "\n")

    # 2. Test Case B: Prime slot (no action)
    decision_b = {
        "decision": "no_action",
        "discount_pct": 0.0,
        "confidence": "high",
        "reasoning": ["High historical fill rate"],
        "source": "llm"
    }
    result_b = generate_outreach(sample_slot, decision_b, live_segments)
    print("=== TEST CASE B: No Action on Real Slot ===")
    print(f"Matched Segment: {result_b['matched_segment']}")
    print("Rendered Message:\n" + result_b["message"])
    print("\n" + "="*50 + "\n")

    print("✅ Outreach layer live data test completed successfully!")