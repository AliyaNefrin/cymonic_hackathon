"""
End-to-End integration test script.
Verifies Data Layer, Reasoning Layer, and Outreach Layer interoperability.
"""
import sys
import os
from datetime import datetime

# Reconfigure stdout for Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from data_layer.data_manager import load_slots, load_segments, append_to_log
from engine.reasoning_llm import evaluate_slot
from outreach_layer.outreach import generate_outreach

print("=" * 60)
print("SPORTS LOT OPTIMISER: END-TO-END INTEGRATION TEST")
print("=" * 60)

# 1. Load Data
print("\n[Step 1] Loading data from data_layer...")
slots_df = load_slots()
segments_df = load_segments()
print(f"-> Successfully loaded {len(slots_df)} slots and {len(segments_df)} segments.")

# 2. Filter Vacant Slots
vacant_slots = slots_df[slots_df["status"] == "vacant"]
print(f"-> Found {len(vacant_slots)} vacant slots awaiting optimization.")

# Test first 3 diverse vacant slots
test_sample = vacant_slots.head(3)

for idx, (_, row) in enumerate(test_sample.iterrows(), 1):
    slot_dict = row.to_dict()
    print("\n" + "-" * 50)
    print(f"[Test {idx}] Evaluating Slot: {slot_dict['slot_id']} | {slot_dict['turf_name']} ({slot_dict['sport']})")
    print(f"           Time: {slot_dict['time_slot']} | Lead Time: {slot_dict['lead_time_hrs']}h | Fill Rate: {float(slot_dict['historical_fill_rate'])*100:.0f}%")

    # 3. LLM Reasoning
    decision = evaluate_slot(slot_dict)
    print(f"\n[Reasoning Output]:")
    print(f"  Decision:   {decision['decision']}")
    print(f"  Discount:   {decision['discount_pct']}%")
    print(f"  Confidence: {decision['confidence']}")
    print(f"  Source:     {decision['source']}")
    print(f"  Reasoning:  {'; '.join(decision['reasoning'])}")

    # 4. Outreach Generation
    outreach = generate_outreach(slot_dict, decision, segments_df)
    print(f"\n[Outreach Output]:")
    print(f"  Matched Segment: {outreach['matched_segment']}")
    print("  Message Preview:")
    for line in outreach['message'].split("\n")[:4]:
        print(f"    {line}")

    # 5. Log decision
    log_entry = {
        "slot_id": slot_dict["slot_id"],
        "decision": decision["decision"],
        "discount_pct": decision["discount_pct"],
        "reasoning": decision["reasoning"],
        "segment_notified": outreach["matched_segment"],
        "source": decision["source"],
        "timestamp": datetime.now().isoformat(),
    }
    append_to_log(log_entry)
    print(f"\n-> Logged decision to booking_log.csv")

print("\n" + "=" * 60)
print("ALL 3 LAYERS SUCCESSFULLY COMMUNICATED END-TO-END!")
print("=" * 60)
