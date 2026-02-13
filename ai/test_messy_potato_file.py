
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import sys

# Redirect stdout to file
sys.stdout = open("messy_results.txt", "w", encoding="utf-8")

from scorer import FarmConditionScorer

# ------------- Configuration -------------
CROP_ID = "POTATO_001"
MODEL_PATH = "model.pkl"
PROFILE_PATH = "crop_profiles.json"
NUM_DAYS = 7
HOURS_PER_DAY = 24
TOTAL_READINGS = NUM_DAYS * HOURS_PER_DAY

def generate_messy_week(seed: int = 123) -> list[dict]:
    rng = np.random.default_rng(seed)
    readings = []
    start_time = datetime(2026, 5, 1, 0, 0, 0)
    base = {
        "soil_moisture": 70, "soil_temp": 18, "air_temp": 22,
        "humidity": 70, "ph": 6.0, "sunlight": 8000,
        "nitrogen": 160, "air_quality": 50
    }
    for i in range(TOTAL_READINGS):
        ts = start_time + timedelta(hours=i)
        noise = rng.normal(0, 1.0) 
        heat_drift = 0
        if 48 <= i < 72:
            heat_drift = (i - 48) * 0.5
        spike = 0
        if i == 100:
            spike = 60
        reading = {
            "timestamp": ts.strftime("%d-%m-%Y %H:%M"),
            "soil_moisture": base["soil_moisture"] + rng.normal(0, 5),
            "soil_temp": base["soil_temp"] + rng.normal(0, 2) + (heat_drift * 0.5),
            "air_temp": base["air_temp"] + rng.normal(0, 3) + heat_drift,
            "humidity": base["humidity"] + rng.normal(0, 5) + spike,
            "ph": base["ph"] + rng.normal(0, 0.2),
            "sunlight": base["sunlight"] + rng.normal(0, 2000),
            "nitrogen": base["nitrogen"] + rng.normal(0, 10),
            "air_quality": base["air_quality"] + rng.normal(0, 20),
        }
        reading["humidity"] = min(100, max(0, reading["humidity"]))
        readings.append(reading)
    return readings

def main():
    print("=" * 70)
    print("  TEST: Messy/Chaotic Potato — Robustness Check")
    print("=" * 70)
    
    try:
        readings = generate_messy_week()
        scorer = FarmConditionScorer(model_path=MODEL_PATH, profile_path=PROFILE_PATH)

        print(f"\nEvaluating {len(readings)} readings...")
        scores = []
        for i in range(1, len(readings) + 1):
            window = readings[:i][-48:]
            result = scorer.predict_score(window, CROP_ID)
            scores.append(result["predicted_score"])

        avg_start = np.mean(scores[:24])
        print(f"\n1. Steady Good State (Day 1): Avg Score = {avg_start:.1f}")
        
        day3_scores = scores[48:72]
        print(f"\n2. Heatwave Drift (Day 3):")
        print(f"   Start: {day3_scores[0]}")
        print(f"   End:   {day3_scores[-1]}")
        
        score_before = scores[99]
        score_during = scores[100]
        score_after = scores[101]
        print(f"\n3. Sudden Spike Event (Hour 100):")
        print(f"   Before: {score_before}")
        print(f"   During: {score_during}")
        print(f"   After:  {score_after}")

        print("\nTEST COMPLETE")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
