"""
Test: Ungrowable Potato Conditions
Generates 1 month (30 days, hourly) of sensor data where conditions are
hostile for potato growth, then feeds it to the trained model to verify
it predicts a very LOW score.

Ungrowable conditions for Potato (POTATO_001):
- Soil moisture:  too low  (~10-25%, ideal is 60-80%)
- Soil temp:      too high (~35-45°C, ideal is 15-20°C)
- Air temp:       too high (~40-50°C, ideal is 18-25°C)
- Humidity:       too low  (~10-25%, ideal is 60-80%)
- pH:             too extreme (~3.0-4.0, ideal is 5.5-6.5)
- Sunlight:       too low  (~100-500 lux, ideal is 6000-12000)
- Nitrogen:       too high (~350-500 ppm, ideal is 120-200)
- Air quality:    too bad  (~450-700 ppm, ideal is 0-150)

Run:  python test_ungrowable_potato.py
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scorer import FarmConditionScorer

# ------------- Configuration -------------
CROP_ID = "POTATO_001"
MODEL_PATH = "model.pkl"
PROFILE_PATH = "crop_profiles.json"
NUM_DAYS = 30
HOURS_PER_DAY = 24
TOTAL_READINGS = NUM_DAYS * HOURS_PER_DAY  # 720 readings

# ------------- Generate ungrowable data -------------
def generate_ungrowable_month(seed: int = 99) -> list[dict]:
    """
    Generate 1 month of hourly sensor readings where every parameter
    is far outside the acceptable range for potato.
    """
    rng = np.random.default_rng(seed)
    readings = []

    start_time = datetime(2026, 4, 1, 0, 0, 0)  # April 1st, 2026

    for hour_idx in range(TOTAL_READINGS):
        ts = start_time + timedelta(hours=hour_idx)

        # Diurnal variation factor (0-1, peaks at noon)
        hour_of_day = ts.hour
        diurnal = np.sin(np.pi * hour_of_day / 24) ** 2

        reading = {
            "timestamp": ts.strftime("%d-%m-%Y %H:%M"),

            # Soil moisture: VERY LOW (10-25%, ideal 60-80%)
            "soil_moisture": rng.uniform(8, 25) - diurnal * 5,

            # Soil temp: VERY HIGH (35-45°C, ideal 15-20°C)
            "soil_temp": rng.uniform(35, 45) + diurnal * 5,

            # Air temp: SCORCHING (40-50°C, ideal 18-25°C)
            "air_temp": rng.uniform(40, 52) + diurnal * 8,

            # Humidity: BONE DRY (10-25%, ideal 60-80%)
            "humidity": rng.uniform(8, 22) - diurnal * 3,

            # pH: VERY ACIDIC (3.0-4.0, ideal 5.5-6.5)
            "ph": rng.uniform(2.5, 4.0),

            # Sunlight: VERY LOW / covered (50-400 lux, ideal 6000-12000)
            "sunlight": rng.uniform(50, 400) * (0.1 + diurnal * 0.3),

            # Nitrogen: TOXIC EXCESS (350-500 ppm, ideal 120-200)
            "nitrogen": rng.uniform(350, 550),

            # Air quality: HEAVILY POLLUTED (500-800 ppm, ideal 0-150)
            "air_quality": rng.uniform(450, 800),
        }

        # Clamp values to physical minimums
        reading["soil_moisture"] = max(0, reading["soil_moisture"])
        reading["humidity"] = max(0, reading["humidity"])
        reading["sunlight"] = max(0, reading["sunlight"])

        readings.append(reading)

    return readings


def main():
    print("=" * 70)
    print("  TEST: Ungrowable Potato — 1 Month of Hostile Conditions")
    print("=" * 70)

    # Load profile for display
    with open(PROFILE_PATH) as f:
        profiles = json.load(f)
    potato = profiles[CROP_ID]

    print(f"\nCrop: {potato['name']} ({CROP_ID})")
    print(f"Duration: {NUM_DAYS} days ({TOTAL_READINGS} hourly readings)")
    print(f"\n--- Ideal vs Ungrowable Ranges ---")
    print(f"{'Parameter':<16} {'Ideal Range':>20} {'Test Values':>20}")
    print("-" * 60)

    param_info = {
        "soil_moisture": ("60-80%",    "5-25%"),
        "soil_temp":     ("15-20°C",   "35-50°C"),
        "air_temp":      ("18-25°C",   "40-60°C"),
        "humidity":      ("60-80%",    "5-22%"),
        "ph":            ("5.5-6.5",   "2.5-4.0"),
        "sunlight":      ("6000-12000","5-120 lux"),
        "nitrogen":      ("120-200",   "350-550 ppm"),
        "air_quality":   ("0-150",     "450-800 ppm"),
    }
    for param, (ideal, test) in param_info.items():
        print(f"  {param:<14} {ideal:>20} {test:>20}")

    # Generate data
    print(f"\nGenerating {TOTAL_READINGS} ungrowable readings...")
    readings = generate_ungrowable_month()

    # Show sample of first 5 readings
    print(f"\n--- Sample Readings (first 5) ---")
    for i, r in enumerate(readings[:5]):
        print(f"  [{i}] ts={r['timestamp']}, "
              f"sm={r['soil_moisture']:.1f}, st={r['soil_temp']:.1f}, "
              f"at={r['air_temp']:.1f}, hum={r['humidity']:.1f}, "
              f"ph={r['ph']:.2f}, sun={r['sunlight']:.0f}, "
              f"N={r['nitrogen']:.0f}, aq={r['air_quality']:.0f}")

    # Initialize scorer
    print(f"\nLoading model from '{MODEL_PATH}'...")
    scorer = FarmConditionScorer(model_path=MODEL_PATH, profile_path=PROFILE_PATH)

    # --- Test 1: Score with the FULL month window ---
    print(f"\n{'=' * 70}")
    print(f"  TEST 1: Full month window ({len(readings)} readings)")
    print(f"{'=' * 70}")

    result = scorer.predict_score(readings, CROP_ID)
    print(f"\n  ★ PREDICTED SCORE: {result['predicted_score']} / 100")
    print(f"\n  Per-parameter breakdown:")
    for param, details in result["per_parameter"].items():
        print(f"    {param:<14}  value={details['value']:>8.2f}  "
              f"norm_score={details['normalized_score']:.3f}  "
              f"trend={details['trend']}")

    # --- Test 2: Score at different time windows ---
    print(f"\n{'=' * 70}")
    print(f"  TEST 2: Scores at different window sizes")
    print(f"{'=' * 70}")

    windows = [1, 6, 24, 72, 168, 360, 720]
    print(f"\n  {'Window':>10}  {'Score':>8}")
    print(f"  {'-'*20}")
    for w in windows:
        if w > len(readings):
            continue
        window_readings = readings[:w]
        result_w = scorer.predict_score(window_readings, CROP_ID)
        label = f"{w}h" if w < 24 else f"{w//24}d"
        print(f"  {label:>10}  {result_w['predicted_score']:>8.1f}")

    # --- Test 3: Week-by-week scores ---
    print(f"\n{'=' * 70}")
    print(f"  TEST 3: Week-by-week scores")
    print(f"{'=' * 70}")

    for week in range(4):
        start = week * 168
        end = min(start + 168, len(readings))
        week_readings = readings[start:end]
        result_week = scorer.predict_score(week_readings, CROP_ID)
        print(f"  Week {week + 1} (hours {start}-{end}): "
              f"Score = {result_week['predicted_score']}")

    # --- Test 4: Compare with ideal-like conditions ---
    print(f"\n{'=' * 70}")
    print(f"  TEST 4: Ungrowable vs Ideal comparison")
    print(f"{'=' * 70}")

    # Create a small set of ideal readings for comparison
    rng_ideal = np.random.default_rng(42)
    ideal_readings = []
    for i in range(24):
        ideal_readings.append({
            "timestamp": f"01-01-2026 {i:02d}:00",
            "soil_moisture": rng_ideal.uniform(62, 78),
            "soil_temp": rng_ideal.uniform(16, 19),
            "air_temp": rng_ideal.uniform(19, 24),
            "humidity": rng_ideal.uniform(62, 78),
            "ph": rng_ideal.uniform(5.6, 6.4),
            "sunlight": rng_ideal.uniform(7000, 11000),
            "nitrogen": rng_ideal.uniform(130, 190),
            "air_quality": rng_ideal.uniform(20, 100),
        })

    result_ideal = scorer.predict_score(ideal_readings, CROP_ID)
    result_bad = scorer.predict_score(readings[:24], CROP_ID)

    print(f"\n  Ideal conditions (24h):     Score = {result_ideal['predicted_score']}")
    print(f"  Ungrowable conditions (24h): Score = {result_bad['predicted_score']}")
    print(f"  Difference:                  {result_ideal['predicted_score'] - result_bad['predicted_score']:.1f} points")

    # --- Verdict ---
    print(f"\n{'=' * 70}")
    print(f"  VERDICT")
    print(f"{'=' * 70}")

    final_score = scorer.predict_score(readings, CROP_ID)["predicted_score"]
    if final_score <= 15:
        verdict = "✅ PASS — Model correctly identifies conditions as UNGROWABLE"
    elif final_score <= 30:
        verdict = "⚠️  MARGINAL — Score is low but could be lower for truly ungrowable conditions"
    else:
        verdict = "❌ FAIL — Model does not recognize these extreme conditions as ungrowable"

    print(f"\n  Final score: {final_score} / 100")
    print(f"  {verdict}")
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
