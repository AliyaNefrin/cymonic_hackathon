import json
import os
import sys
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env if present
load_dotenv()

# Initialize Groq client safely
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

SYSTEM_PROMPT = """You are an expert revenue management agent for sports turf arenas. Your objective is to maximize turf revenue by deciding the optimal outreach and pricing strategy for an empty slot, balancing occupancy risk against margin preservation.

You will be given the details of a single vacant slot, including its turf name, sport, date, time slot, lead time in hours, base price, cost to operate, computed margin ratio, historical fill rate, and customer tags.

### DECISION OPTIONS
You must choose EXACTLY ONE of the following 4 decision strings (no other values allowed):
- "no_action": The slot has a high probability of filling on its own, or lead time is too far out to justify intervention. Do not notify or discount.
- "notify_only": The slot has moderate fill probability or moderate lead time. Alert relevant customers without offering any discount (protecting margin).
- "notify_small_discount": The slot is at risk of remaining empty and margin room permits. Offer a modest incentive (5% to 15% discount) to drive booking.
- "notify_large_discount": The slot is at high risk of remaining empty (low historical fill rate and short lead time), but margin ratio is sufficient. Offer a substantial incentive (16% to 30% discount) to avoid a total loss of revenue.

### CORE BUSINESS RULES
1. NEVER discount a slot if historical_fill_rate is high (e.g. >= 0.75), regardless of lead time.
2. Short lead time alone does NOT justify a large discount if historical fill rate is healthy or if margin ratio is thin.
3. The discount percentage must strictly reflect margin headroom: never suggest a discount that wipes out operational margin.
4. If "no_action" or "notify_only" is chosen, "discount_pct" MUST be 0.0.
5. If "notify_small_discount" is chosen, "discount_pct" must be between 5.0 and 15.0.
6. If "notify_large_discount" is chosen, "discount_pct" must be between 16.0 and 30.0. Max discount allowed across all decisions is 30.0%.

### OUTPUT FORMAT
You must respond with a valid JSON object matching this exact structure:
{
  "decision": "no_action" | "notify_only" | "notify_small_discount" | "notify_large_discount",
  "discount_pct": <float between 0.0 and 30.0>,
  "confidence": "low" | "medium" | "high",
  "reasoning": [
    "<short bullet point citing specific slot numbers (lead time, fill rate, or margin)>",
    "<short bullet point explaining why this action protects revenue or margin>"
  ]
}"""


def _format_user_prompt(slot: dict, margin_ratio: float) -> str:
    """Formats slot data and precomputed margin ratio into the user prompt."""
    return f"""Evaluate the following empty sports turf slot:
- Slot ID: {slot.get('slot_id', 'N/A')}
- Turf Name: {slot.get('turf_name', 'N/A')}
- Sport: {slot.get('sport', 'N/A')}
- Date: {slot.get('date', 'N/A')} ({slot.get('day_of_week', 'N/A')})
- Time Slot: {slot.get('time_slot', 'N/A')}
- Lead Time: {slot.get('lead_time_hrs', 0)} hours
- Base Price: ${float(slot.get('base_price', 0)):.2f}
- Cost to Operate: ${float(slot.get('cost_to_operate', 0)):.2f}
- Margin Ratio: {margin_ratio * 100:.1f}%
- Historical Fill Rate: {float(slot.get('historical_fill_rate', 0)) * 100:.1f}%
- Tags: {slot.get('tags', 'N/A')}

Respond ONLY with the required JSON object."""


def _fallback_rule_based(slot: dict, margin_ratio: float) -> dict:
    """
    Deterministic rule-based fallback when LLM is unavailable or fails.
    Returns the exact same contract shape expected by the application.
    """
    fill_rate = float(slot.get("historical_fill_rate", 0.5))
    lead_time = float(slot.get("lead_time_hrs", 24))

    # Rule 1: High fill rate slots naturally fill; no discount needed
    if fill_rate >= 0.70:
        return {
            "decision": "no_action",
            "discount_pct": 0.0,
            "confidence": "high",
            "reasoning": [
                f"Historical fill rate is strong at {fill_rate * 100:.0f}%, indicating organic demand.",
                "Intervention is unnecessary and preserves standard pricing.",
            ],
            "source": "rule_based_fallback",
        }

    # Rule 2: Long lead time allows time for organic bookings
    if lead_time > 48:
        return {
            "decision": "notify_only",
            "discount_pct": 0.0,
            "confidence": "medium",
            "reasoning": [
                f"Lead time is comfortable at {lead_time:.0f} hours ahead.",
                "Notification alerts customers early while keeping prices intact.",
            ],
            "source": "rule_based_fallback",
        }

    # Rule 3: Urgent slot with low historical fill rate and healthy margin headroom
    if lead_time <= 12 and fill_rate < 0.40 and margin_ratio >= 0.35:
        return {
            "decision": "notify_large_discount",
            "discount_pct": 20.0,
            "confidence": "medium",
            "reasoning": [
                f"Urgent slot ({lead_time:.0f}h remaining) with low fill rate ({fill_rate * 100:.0f}%).",
                f"Margin ratio is healthy at {margin_ratio * 100:.0f}%, allowing a 20% promotional discount.",
            ],
            "source": "rule_based_fallback",
        }

    # Rule 4: Moderate urgency with adequate margin room
    if margin_ratio >= 0.15:
        return {
            "decision": "notify_small_discount",
            "discount_pct": 10.0,
            "confidence": "low",
            "reasoning": [
                f"Slot has moderate fill risk ({fill_rate * 100:.0f}%) with {lead_time:.0f}h lead time.",
                f"Margin ratio of {margin_ratio * 100:.0f}% supports a conservative 10% discount.",
            ],
            "source": "rule_based_fallback",
        }

    # Rule 5: Margin is too thin to discount without risking operational loss
    return {
        "decision": "notify_only",
        "discount_pct": 0.0,
        "confidence": "medium",
        "reasoning": [
            f"Margin ratio is thin at {margin_ratio * 100:.0f}%, preventing safe discounting.",
            "Notification reaches targeted players without eroding operational profit.",
        ],
        "source": "rule_based_fallback",
    }


def evaluate_slot(slot: dict) -> dict:
    """
    Evaluates a single empty sports turf slot and returns an optimal pricing
    and outreach decision.

    slot: a dict with keys matching slots.csv columns —
          slot_id, turf_name, sport, date, day_of_week, time_slot,
          lead_time_hrs, base_price, cost_to_operate, historical_fill_rate, tags

    Returns:
    {
        "decision": str,        # "no_action" | "notify_only" | "notify_small_discount" | "notify_large_discount"
        "discount_pct": float,  # 0.0 - 30.0
        "confidence": str,      # "low" | "medium" | "high"
        "reasoning": list[str], # 2-3 short bullets referencing the actual numbers
        "source": str,          # "llm" | "rule_based_fallback"
    }
    """
    # 1. Compute margin ratio deterministically in Python
    base_price = float(slot.get("base_price", 0.0))
    cost = float(slot.get("cost_to_operate", 0.0))
    margin_ratio = (base_price - cost) / base_price if base_price > 0 else 0.0

    # 2. If Groq client is not initialized, route immediately to deterministic fallback
    if client is None:
        return _fallback_rule_based(slot, margin_ratio)

    # 3. Call Groq with low temperature and forced JSON mode
    try:
        model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _format_user_prompt(slot, margin_ratio)},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)

        return {
            "decision": parsed.get("decision", "no_action"),
            "discount_pct": float(parsed.get("discount_pct", 0.0)),
            "confidence": parsed.get("confidence", "medium"),
            "reasoning": parsed.get("reasoning", []),
            "source": "llm",
        }
    except Exception:
        # Graceful degradation on network timeout, rate limits, or parse errors
        return _fallback_rule_based(slot, margin_ratio)


if __name__ == "__main__":
    # Ensure UTF-8 output encoding for Windows terminal
    if sys.stdout.encoding != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 60)
    print("REASONING ENGINE: EVALUATING REAL SLOTS FROM DATA LAYER")
    print("=" * 60)

    # Ensure project root is in sys.path when run directly
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    try:
        from data_layer.data_manager import load_slots
        slots_df = load_slots()
        vacant_df = slots_df[slots_df["status"] == "vacant"]
        sample_slots = vacant_df.head(4).to_dict(orient="records")
        print(f"Loaded {len(vacant_df)} vacant slots from data_layer/slots.csv. Evaluating sample:\n")
    except Exception as e:
        print(f"Could not load slots from data_layer ({e}).")
        sample_slots = []

    for slot in sample_slots:
        print(f"\n--- Evaluating Slot {slot.get('slot_id')} ({slot.get('turf_name')} - {slot.get('sport')}) ---")
        print(f"Time: {slot.get('time_slot')} | Lead: {slot.get('lead_time_hrs')}h | Fill Rate: {float(slot.get('historical_fill_rate', 0))*100:.0f}% | Margin: ${float(slot.get('base_price',0)) - float(slot.get('cost_to_operate',0)):.2f}")
        res = evaluate_slot(slot)
        print(f"Decision:     {res['decision']}")
        print(f"Discount:     {res['discount_pct']}%")
        print(f"Confidence:   {res['confidence']}")
        print(f"Source:       {res['source']}")
        print("Reasoning:")
        for bullet in res["reasoning"]:
            print(f"  * {bullet}")
    print("\n" + "=" * 60)



