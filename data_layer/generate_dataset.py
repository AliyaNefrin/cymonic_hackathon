"""
generate_dataset.py
Generates synthetic but realistic turf-booking data for the Sports Lot Optimiser.
Part of the Data Layer (Person A).

Outputs:
1. slots.csv (in data_layer/)
2. customer_segments.csv (in data_layer/)
3. booking_log.csv (in data_layer/)
"""

import os
from pathlib import Path
import random
from datetime import date, timedelta
import pandas as pd
import numpy as np

# Fixed seed for 100% reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

DATA_DIR = Path(__file__).parent.resolve()

TURFS = [
    {"name": "Apex Arena", "sports": ["Football", "Cricket"]},
    {"name": "Velocity Turf", "sports": ["Football", "Basketball"]},
    {"name": "Champions Court", "sports": ["Badminton", "Basketball"]},
]

SPORT_PRICING = {
    "Football": {"base_min": 900, "base_max": 1300, "cost_ratio": (0.35, 0.45)},
    "Cricket": {"base_min": 1100, "base_max": 1500, "cost_ratio": (0.35, 0.45)},
    "Basketball": {"base_min": 700, "base_max": 1000, "cost_ratio": (0.30, 0.40)},
    "Badminton": {"base_min": 500, "base_max": 800, "cost_ratio": (0.30, 0.40)},
}

# 2-week window: Mon 2026-09-14 through Sun 2026-09-27
START_DATE = date(2026, 9, 14)
NUM_DAYS = 14

TIME_SLOTS_WEEKDAY = [
    # Morning
    "08:00-09:00", "09:00-10:00",
    # Afternoon (Low-fill target)
    "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
    # Evening (Peak)
    "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
]

TIME_SLOTS_WEEKEND = [
    # Morning
    "07:00-08:00", "08:00-09:00", "09:00-10:00", "10:00-11:00",
    # Afternoon
    "12:00-13:00", "14:00-15:00", "15:00-16:00", "16:00-17:00",
    # Evening (Peak)
    "17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"
]

AFTERNOON_HOURS = {"12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00", "16:00-17:00"}
EVENING_HOURS = {"17:00-18:00", "18:00-19:00", "19:00-20:00", "20:00-21:00", "21:00-22:00"}


def generate_slots():
    slots = []
    slot_counter = 1001

    for day_offset in range(NUM_DAYS):
        current_date = START_DATE + timedelta(days=day_offset)
        day_of_week = current_date.strftime("%A")
        is_weekend = day_of_week in ("Saturday", "Sunday")
        
        daily_time_slots = TIME_SLOTS_WEEKEND if is_weekend else TIME_SLOTS_WEEKDAY
        
        for turf in TURFS:
            turf_name = turf["name"]
            available_sports = turf["sports"]
            
            slots_to_schedule = 4 if not is_weekend else 5
            selected_times = sorted(
                random.sample(daily_time_slots, min(slots_to_schedule, len(daily_time_slots)))
            )
            
            for time_slot in selected_times:
                sport = random.choice(available_sports)
                pricing = SPORT_PRICING[sport]
                
                raw_price = random.randint(pricing["base_min"], pricing["base_max"])
                base_price = float(round(raw_price / 50) * 50)
                
                cost_ratio = random.uniform(*pricing["cost_ratio"])
                cost_to_operate = float(round((base_price * cost_ratio) / 10) * 10)
                
                lead_time_hrs = int(random.choice([4, 6, 8, 12, 18, 24, 36, 48, 72]))
                
                is_afternoon = time_slot in AFTERNOON_HOURS
                is_evening = time_slot in EVENING_HOURS
                
                if not is_weekend and is_afternoon:
                    historical_fill_rate = round(float(np.clip(np.random.normal(0.28, 0.07), 0.15, 0.45)), 2)
                    tags = "weekday, low-demand, afternoon, low-fill"
                    status = "vacant" if random.random() < 0.80 else "booked"
                elif is_evening or is_weekend:
                    historical_fill_rate = round(float(np.clip(np.random.normal(0.80, 0.08), 0.65, 0.95)), 2)
                    tags = "weekend, high-demand" if is_weekend else "weekday, peak"
                    status = "booked" if random.random() < 0.80 else "vacant"
                else:
                    historical_fill_rate = round(float(np.clip(np.random.normal(0.48, 0.06), 0.35, 0.60)), 2)
                    tags = "weekday, regular"
                    status = "vacant" if random.random() < 0.50 else "booked"
                
                slot_id = f"S{slot_counter}"
                slot_counter += 1
                
                slots.append({
                    "slot_id": slot_id,
                    "turf_name": turf_name,
                    "sport": sport,
                    "date": current_date.strftime("%Y-%m-%d"),
                    "day_of_week": day_of_week,
                    "time_slot": time_slot,
                    "lead_time_hrs": lead_time_hrs,
                    "base_price": base_price,
                    "cost_to_operate": cost_to_operate,
                    "historical_fill_rate": historical_fill_rate,
                    "status": status,
                    "tags": tags
                })

    return pd.DataFrame(slots)


def generate_segments():
    segments = [
        {
            "segment_id": "SEG_01",
            "segment_name": "Football Weekday Regulars",
            "sport_pref": "Football",
            "preferred_time_band": "17:00-20:00",
            "price_sensitivity": "medium",
            "size": 65,
        },
        {
            "segment_id": "SEG_02",
            "segment_name": "Weekend Football Players",
            "sport_pref": "Football",
            "preferred_time_band": "18:00-22:00",
            "price_sensitivity": "low",
            "size": 90,
        },
        {
            "segment_id": "SEG_03",
            "segment_name": "Cricket Afternoon Groups",
            "sport_pref": "Cricket",
            "preferred_time_band": "12:00-17:00",
            "price_sensitivity": "high",
            "size": 40,
        },
        {
            "segment_id": "SEG_04",
            "segment_name": "Price Sensitive Players",
            "sport_pref": "Football",
            "preferred_time_band": "12:00-17:00",
            "price_sensitivity": "high",
            "size": 75,
        },
        {
            "segment_id": "SEG_05",
            "segment_name": "Evening Sports Regulars",
            "sport_pref": "Basketball",
            "preferred_time_band": "17:00-20:00",
            "price_sensitivity": "medium",
            "size": 45,
        },
        {
            "segment_id": "SEG_06",
            "segment_name": "Badminton Midday Smashers",
            "sport_pref": "Badminton",
            "preferred_time_band": "12:00-17:00",
            "price_sensitivity": "high",
            "size": 35,
        },
        {
            "segment_id": "SEG_07",
            "segment_name": "Weekend Prime Cricket",
            "sport_pref": "Cricket",
            "preferred_time_band": "17:00-22:00",
            "price_sensitivity": "low",
            "size": 55,
        },
    ]
    return pd.DataFrame(segments)


def main():
    slots_df = generate_slots()
    segments_df = generate_segments()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    slots_path = DATA_DIR / "slots.csv"
    segments_path = DATA_DIR / "customer_segments.csv"
    log_path = DATA_DIR / "booking_log.csv"

    slots_df.to_csv(slots_path, index=False)
    segments_df.to_csv(segments_path, index=False)

    if not log_path.exists() or log_path.stat().st_size == 0:
        log_headers = "slot_id,decision,discount_pct,reasoning,segment_notified,source,timestamp\n"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(log_headers)

    total_slots = len(slots_df)
    vacant_slots = int((slots_df["status"] == "vacant").sum())
    booked_slots = int((slots_df["status"] == "booked").sum())
    avg_fill_rate = float(slots_df["historical_fill_rate"].mean())

    weekday_afternoon_mask = (
        ~slots_df["day_of_week"].isin(["Saturday", "Sunday"])
        & slots_df["time_slot"].isin(AFTERNOON_HOURS)
    )
    num_weekday_afternoon = int(weekday_afternoon_mask.sum())
    avg_weekday_afternoon_fill = float(
        slots_df.loc[weekday_afternoon_mask, "historical_fill_rate"].mean()
    )

    evening_weekend_mask = (
        slots_df["day_of_week"].isin(["Saturday", "Sunday"])
        | slots_df["time_slot"].isin(EVENING_HOURS)
    )
    avg_evening_weekend_fill = float(
        slots_df.loc[evening_weekend_mask, "historical_fill_rate"].mean()
    )

    print("=" * 60)
    print("DATASET GENERATION SUMMARY (data_layer)")
    print("=" * 60)
    print(f"Total slots:                         {total_slots}")
    print(f"Vacant slots:                        {vacant_slots}")
    print(f"Booked slots:                        {booked_slots}")
    print(f"Average historical fill rate:        {avg_fill_rate:.3f}")
    print(f"Number of weekday afternoon slots:   {num_weekday_afternoon}")
    print(f"Average weekday afternoon fill rate: {avg_weekday_afternoon_fill:.3f}")
    print(f"Average evening/weekend fill rate:   {avg_evening_weekend_fill:.3f}")
    print(f"Customer segments created:           {len(segments_df)}")
    print("=" * 60)
    print("Generated files:")
    print(f" - {slots_path}")
    print(f" - {segments_path}")
    print(f" - {log_path}")


if __name__ == "__main__":
    main()
