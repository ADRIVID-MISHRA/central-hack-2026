"""
Test: Messy/Chaotic Potato Conditions (V2 - Truly Extreme)
Simulates realistic, noisy, and chaotic data to test model robustness.
This version uses ACTUALLY extreme values that go well beyond acceptable ranges.

Scenarios:
1. Steady ideal state (Day 1)              → Expect ~95-100
2. Extreme heatwave (Day 3, air=50°C)      → Expect big drop
3. Sudden humidity spike (100%+)            → Expect noticeable dip
4. Gradual total collapse (Days 5-7)        → Expect score to crash

Run:  python test_messy_potato.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
from scorer import FarmConditionScorer

# ------------- Configuration -------------
CROP_ID = "POTATO_001"
MODEL_PATH = "model.pkl"
PROFILE_PATH = "crop_profiles.json"
NUM_DAYS = 7
HOURS_PER_DAY = 24
TOTAL_READINGS = NUM_DAYS * HOURS_PER_DAY  # 168 readings

def generate_messy_week(seed: int = 123) -> list[dict]:
    """
    Generate 1 week of data with 4 distinct phases:
    - Day 1-2:  Perfect conditions (baseline)
    - Day 3:    Extreme heatwave (air_temp 45-55°C, way past accept_max=35)
    - Day 4:    Recovery + random humidity spike at hour 100
    - Day 5-7:  Total collapse (everything goes bad gradually)
    """
    rng = np.random.default_rng(seed)
    readings = []
    start_time = datetime(2026, 5, 1, 0, 0, 0)

    for i in range(TOTAL_READINGS):
        ts = start_time + timedelta(hours=i)
        day = i // 24  # 0-indexed day number

        if day < 2:
            # --- PHASE 1: Perfect conditions ---
            reading = {
                "soil_moisture": rng.uniform(65, 75),
                "soil_temp": rng.uniform(16, 19),
                "air_temp": rng.uniform(19, 24),
                "humidity": rng.uniform(65, 75),
                "ph": rng.uniform(5.8, 6.2),
                "sunlight": rng.uniform(7000, 11000),
                "nitrogen": rng.uniform(140, 180),
                "air_quality": rng.uniform(20, 80),
            }
        elif day == 2:
            # --- PHASE 2: EXTREME heatwave ---
            # air_temp: 45-55°C (accept_max is 35°C — way beyond)
            # soil_temp: 30-40°C (accept_max is 30°C)
            # humidity crashes to 10-20% (accept_min is 40%)
            # soil_moisture drops to 15-25% (accept_min is 40%)
            hour_in_day = i % 24
            heat_factor = np.sin(np.pi * hour_in_day / 24) ** 2  # peaks at noon
            reading = {
                "soil_moisture": rng.uniform(15, 30),
                "soil_temp": rng.uniform(28, 40) + heat_factor * 5,
                "air_temp": rng.uniform(42, 55) + heat_factor * 8,
                "humidity": rng.uniform(8, 20),
                "ph": rng.uniform(5.8, 6.2),  # pH stays normal
                "sunlight": rng.uniform(7000, 11000),  # sunlight stays normal
                "nitrogen": rng.uniform(140, 180),  # nitrogen normal
                "air_quality": rng.uniform(20, 80),  # air quality normal
            }
        elif day == 3:
            # --- PHASE 3: Recovery + sudden spike at hour 100 ---
            reading = {
                "soil_moisture": rng.uniform(60, 75),
                "soil_temp": rng.uniform(16, 20),
                "air_temp": rng.uniform(20, 25),
                "humidity": rng.uniform(62, 78),
                "ph": rng.uniform(5.8, 6.2),
                "sunlight": rng.uniform(7000, 11000),
                "nitrogen": rng.uniform(140, 180),
                "air_quality": rng.uniform(20, 80),
            }
            # Hour 100 = day 4, hour 4 → spike ALL params simultaneously
            if i == 100:
                reading["humidity"] = 100
                reading["soil_moisture"] = 100  # Flooding
                reading["air_quality"] = 600    # Toxic pollution burst
                reading["nitrogen"] = 450       # Toxic nitrogen
        else:
            # --- PHASE 4: Total collapse (Days 5-7) ---
            # Every parameter drifts further from ideal each hour
            collapse_progress = (i - 96) / (TOTAL_READINGS - 96)  # 0.0 → 1.0
            reading = {
                "soil_moisture": 70 - collapse_progress * 60,   # 70% → 10%
                "soil_temp": 18 + collapse_progress * 25,       # 18°C → 43°C
                "air_temp": 22 + collapse_progress * 35,        # 22°C → 57°C
                "humidity": 70 - collapse_progress * 55,         # 70% → 15%
                "ph": 6.0 - collapse_progress * 3,               # 6.0 → 3.0
                "sunlight": 8000 - collapse_progress * 7500,     # 8000 → 500 lux
                "nitrogen": 160 + collapse_progress * 300,       # 160 → 460 ppm
                "air_quality": 50 + collapse_progress * 600,     # 50 → 650 ppm
            }
            # Add noise
            for key in reading:
                if key != "timestamp":
                    reading[key] += rng.normal(0, abs(reading[key]) * 0.03)

        # Clamp physics
        reading["soil_moisture"] = max(0, min(100, reading["soil_moisture"]))
        reading["humidity"] = max(0, min(100, reading["humidity"]))
        reading["sunlight"] = max(0, reading["sunlight"])
        reading["air_quality"] = max(0, reading["air_quality"])
        reading["nitrogen"] = max(0, reading["nitrogen"])

        reading["timestamp"] = ts.strftime("%d-%m-%Y %H:%M")
        readings.append(reading)

    return readings


def main():
    print("=" * 70)
    print("  TEST: Messy/Chaotic Potato V2 — Extreme Robustness Check")
    print("=" * 70)

    readings = generate_messy_week()
    scorer = FarmConditionScorer(model_path=MODEL_PATH, profile_path=PROFILE_PATH)

    print(f"\nEvaluating {len(readings)} readings across 4 phases...")

    # Track score at each hour
    scores = []
    for i in range(1, len(readings) + 1):
        window = readings[:i][-48:]  # last 48h window
        result = scorer.predict_score(window, CROP_ID)
        scores.append(result["predicted_score"])

    # ========== ANALYSIS ==========

    # 1. Steady State (Day 1-2, hours 0-47)
    avg_baseline = np.mean(scores[:48])
    print(f"\n{'='*60}")
    print(f"  PHASE 1: Ideal Baseline (Days 1-2)")
    print(f"{'='*60}")
    print(f"  Avg Score: {avg_baseline:.1f}")
    if avg_baseline > 85:
        print("  ✅ PASS: Model correctly identifies ideal conditions.")
    else:
        print("  ❌ FAIL: Score too low for ideal conditions.")

    # 2. Extreme Heatwave (Day 3, hours 48-71)
    heat_start = scores[48]
    heat_mid = scores[59]  # noon
    heat_end = scores[71]
    heat_drop = avg_baseline - np.mean(scores[48:72])
    print(f"\n{'='*60}")
    print(f"  PHASE 2: Extreme Heatwave (Day 3)")
    print(f"  air_temp=45-63°C, soil_moisture=15-30%, humidity=8-20%")
    print(f"{'='*60}")
    print(f"  Start:   {heat_start:.1f}")
    print(f"  Noon:    {heat_mid:.1f}")
    print(f"  End:     {heat_end:.1f}")
    print(f"  Drop from baseline: -{heat_drop:.1f} pts")
    if heat_drop > 20:
        print("  ✅ PASS: Model reacted strongly to extreme heat.")
    elif heat_drop > 10:
        print("  ⚠️  MARGINAL: Model noticed the heat but reaction is mild.")
    else:
        print("  ❌ FAIL: Model ignored extreme heat conditions.")

    # 3. Recovery + Spike (Day 4, hour 100)
    recovery_avg = np.mean(scores[72:96])
    spike_before = scores[99]
    spike_during = scores[100]
    spike_after = scores[101] if len(scores) > 101 else scores[-1]
    spike_drop = spike_before - spike_during
    print(f"\n{'='*60}")
    print(f"  PHASE 3: Recovery + Multi-Param Spike (Hour 100)")
    print(f"  humidity=100%, soil_moisture=100%, air_quality=600, N=450")
    print(f"{'='*60}")
    print(f"  Recovery avg (Day 4): {recovery_avg:.1f}")
    print(f"  Before spike: {spike_before:.1f}")
    print(f"  During spike: {spike_during:.1f}")
    print(f"  After spike:  {spike_after:.1f}")
    print(f"  Spike impact: -{spike_drop:.1f} pts")
    if spike_drop > 5:
        print("  ✅ PASS: Model detected the multi-parameter spike.")
    elif spike_drop > 1:
        print("  ⚠️  MARGINAL: Small reaction to the spike.")
    else:
        print("  ❌ FAIL: Model completely ignored the spike.")

    # 4. Total Collapse (Days 5-7, hours 96-167)
    collapse_start = scores[96]
    collapse_mid = scores[132]
    collapse_end = scores[-1]
    total_drop = collapse_start - collapse_end
    print(f"\n{'='*60}")
    print(f"  PHASE 4: Total Collapse (Days 5-7)")
    print(f"  All params drift to extreme bad values")
    print(f"{'='*60}")
    print(f"  Start (Day 5): {collapse_start:.1f}")
    print(f"  Mid (Day 6):   {collapse_mid:.1f}")
    print(f"  End (Day 7):   {collapse_end:.1f}")
    print(f"  Total drop:    -{total_drop:.1f} pts")
    if collapse_end < 20:
        print("  ✅ PASS: Model correctly shows near-zero score at total collapse.")
    elif collapse_end < 40:
        print("  ⚠️  MARGINAL: Score dropped but not enough for total failure.")
    else:
        print("  ❌ FAIL: Model doesn't recognize total environmental collapse.")

    # ========== OVERALL VERDICT ==========
    print(f"\n{'='*70}")
    print(f"  OVERALL VERDICT")
    print(f"{'='*70}")
    passes = 0
    if avg_baseline > 85: passes += 1
    if heat_drop > 20: passes += 1
    if spike_drop > 5: passes += 1
    if collapse_end < 20: passes += 1

    print(f"\n  Tests passed: {passes}/4")
    if passes == 4:
        print("  ✅ MODEL IS ROBUST — R² of 0.96 is legitimate.")
    elif passes >= 3:
        print("  ⚠️  MODEL IS MOSTLY ROBUST — Minor sensitivity gaps.")
    else:
        print("  ❌ MODEL HAS ISSUES — May need retraining with more extreme data.")

    print(f"\n{'='*70}")


if __name__ == "__main__":
    main()
