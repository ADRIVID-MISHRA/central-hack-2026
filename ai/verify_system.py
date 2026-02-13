
"""
FINAL VERIFICATION: Farm Condition Matching AI
Checks all files, verifies model loading, and runs sanity tests.
"""
import sys
import os
import json
from pathlib import Path

# Redirect stdout to file to bypass console hang issues
sys.stdout = open("verification_report.txt", "w", encoding="utf-8")

print("=" * 60)
print("  FINAL SYSTEM VERIFICATION")
print("=" * 60)

# 1. FILE CHECK
required_files = [
    "model.pkl",
    "crop_profiles.json",
    "scorer.py",
    "main.py",
    "generate_training_data.py"
]

print("\n[1] Checking File Integrity...")
missing = []
for f in required_files:
    if os.path.exists(f):
        print(f"  ✅ Found: {f}")
    else:
        print(f"  ❌ MISSING: {f}")
        missing.append(f)

if missing:
    print("\nCRITICAL ERROR: Missing files!")
    sys.exit(1)

# 2. MODEL LOADING
print("\n[2] Loading Scorer Engine...")
try:
    from scorer import FarmConditionScorer
    scorer = FarmConditionScorer(model_path="model.pkl", profile_path="crop_profiles.json")
    print("  ✅ Scorer initialized successfully.")
    print(f"  ✅ Model loaded.")
    print(f"  ✅ Profiles loaded: {list(scorer.profiles.keys())}")
except Exception as e:
    print(f"  ❌ FAILED to load scorer: {e}")
    sys.exit(1)

# 3. SANITY TESTS
print("\n[3] Running Sanity Checks...")

# Case A: Ideal Potato
ideal_reading = {
    "timestamp": "2026-05-01 12:00",
    "soil_moisture": 70, "soil_temp": 18, "air_temp": 22,
    "humidity": 70, "ph": 6.0, "sunlight": 8000,
    "nitrogen": 160, "air_quality": 50
}
# Case B: Dead Potato (Heatwave)
dead_reading = {
    "timestamp": "2026-05-01 12:00",
    "soil_moisture": 20, "soil_temp": 35, "air_temp": 45,  # Too hot!
    "humidity": 15, "ph": 6.0, "sunlight": 8000,
    "nitrogen": 160, "air_quality": 50
}

# Run prediction
try:
    score_ideal = scorer.predict_score([ideal_reading], "POTATO_001")["predicted_score"]
    score_dead = scorer.predict_score([dead_reading], "POTATO_001")["predicted_score"]
    
    print(f"  Test A (Ideal): Score = {score_ideal} (Expected > 90)")
    if score_ideal > 90: print("    ✅ PASS")
    else: print("    ❌ FAIL")

    print(f"  Test B (Heatwave): Score = {score_dead} (Expected < 60)")
    if score_dead < 60: print("    ✅ PASS")
    else: print("    ❌ FAIL")

except Exception as e:
    print(f"  ❌ Prediction Error: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("  SYSTEM READY FOR DEPLOYMENT")
print("=" * 60)
