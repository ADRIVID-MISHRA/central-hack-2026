"""
Test: Ideal Potato Conditions
Generates 1 month (30 days, hourly) of sensor data where conditions are
PERFECT for potato growth, then feeds it to the trained model to verify
it predicts a very HIGH score.

Ideal conditions for Potato (POTATO_001):
- Soil moisture:  60-80%
- Soil temp:      15-20°C
- Air temp:       18-25°C
- Humidity:       60-80%
- pH:             5.5-6.5
- Sunlight:       6000-12000 lux
- Nitrogen:       120-200 ppm
- Air quality:    0-150 ppm

Run:  python test_ideal_potato.py
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

# ------------- Generate ideal data -------------
def generate_ideal_month(seed: int = 42) -> list[dict]:
    """
    Generate 1 month of hourly sensor readings where every parameter
    is within the IDEAL range for potato.
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

            # Soil moisture: Ideal 60-80%
            "soil_moisture": rng.uniform(62, 78),

            # Soil temp: Ideal 15-20°C
            "soil_temp": rng.uniform(16, 19) + diurnal * 1,

            # Air temp: Ideal 18-25°C
            "air_temp": rng.uniform(19, 23) + diurnal * 2,

            # Humidity: Ideal 60-80%
            "humidity": rng.uniform(62, 78) - diurnal * 5,

            # pH: Ideal 5.5-6.5
            "ph": rng.uniform(5.8, 6.2),

            # Sunlight: Ideal 6000-12000 lux
            # Night is 0, Day is high. But for "ideal", we ensure average is good.
            # Realistically, plants need night. But our simple scorer might average.
            # Let's give good sunlight during day and 0 at night, but consistently within bounds when sun is out.
            "sunlight": 0 if (hour_of_day < 6 or hour_of_day > 18) else rng.uniform(7000, 11000),

            # Nitrogen: Ideal 120-200 ppm
            "nitrogen": rng.uniform(140, 180),

            # Air quality: Ideal 0-150 ppm
            "air_quality": rng.uniform(20, 100),
        }
        
        # Override sunlight zero for "simple ideal check" if scorer penalizes 0 blindly
        # (Though biologically correct, simple math models might dislike 0 if range is 6000-12000)
        # Checking crop_profiles.json: min acceptable is 3000. 
        # So 0 at night is "bad" by strict parameter ranges.
        # To test "Perfect Conditions" as far as the Scorer Logic sees it (which might aggregate simplisticly),
        # let's keep it safely inside the ideal range even at night for this specific test,
        # OR acknowledge that the model might dip score at night.
        # Let's fake "always day" or "grow lights" to prove the MAX score potential.
        reading["sunlight"] = rng.uniform(7000, 11000)

        readings.append(reading)

    return readings


def main():
    print("=" * 70)
    print("  TEST: Ideal Potato — 1 Month of Perfect Conditions")
    print("=" * 70)

    # Load profile for display
    with open(PROFILE_PATH) as f:
        profiles = json.load(f)
    potato = profiles[CROP_ID]

    print(f"\nCrop: {potato['name']} ({CROP_ID})")
    print(f"Duration: {NUM_DAYS} days ({TOTAL_READINGS} hourly readings)")
    print(f"\n--- Ideal vs Test Ranges ---")
    print(f"{'Parameter':<16} {'Ideal Range':>20} {'Test Values':>20}")
    print("-" * 60)

    param_info = {
        "soil_moisture": ("60-80%",    "62-78%"),
        "soil_temp":     ("15-20°C",   "16-20°C"),
        "air_temp":      ("18-25°C",   "19-25°C"),
        "humidity":      ("60-80%",    "~60-78%"),
        "ph":            ("5.5-6.5",   "5.8-6.2"),
        "sunlight":      ("6000-12000","7000-11000"),
        "nitrogen":      ("120-200",   "140-180 ppm"),
        "air_quality":   ("0-150",     "20-100 ppm"),
    }
    for param, (ideal, test) in param_info.items():
        print(f"  {param:<14} {ideal:>20} {test:>20}")

    # Generate data
    print(f"\nGenerating {TOTAL_READINGS} ideal readings...")
    readings = generate_ideal_month()

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

    # --- Verdict ---
    print(f"\n{'=' * 70}")
    print(f"  VERDICT")
    print(f"{'=' * 70}")

    final_score = scorer.predict_score(readings, CROP_ID)["predicted_score"]
    if final_score >= 85:
        verdict = "✅ PASS — Model correctly identifies conditions as EXCELLENT"
    elif final_score >= 70:
        verdict = "⚠️  MARGINAL — Score is good but should be higher for perfect conditions"
    else:
        verdict = "❌ FAIL — Model gives low score despite perfect conditions"

    print(f"\n  Final score: {final_score} / 100")
    print(f"  {verdict}")
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
