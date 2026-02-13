"""
Scoring Engine (Inference) for Farm Condition Matching AI.
(Crop-Agnostic Version)

Normalizes raw sensor values using the target crop's profile ranges,
then feeds the normalized 0-1 features to the trained model.

Works for ANY crop — just add a profile to crop_profiles.json.
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone


# Base sensor parameter names (from ESP32 / DB)
SENSOR_PARAMS = [
    "soil_moisture", "soil_temp", "air_temp", "humidity",
    "ph", "sunlight", "nitrogen", "air_quality",
]

# Normalized score column names (what the model expects)
SCORE_PARAMS = [
    "soil_moisture_score", "soil_temp_score", "air_temp_score",
    "humidity_score", "ph_score", "sunlight_score",
    "nitrogen_score", "air_quality_score",
]

FEATURE_COLUMNS = [
    # 8 normalized current scores
    *SCORE_PARAMS,
    # 8 rolling averages of normalized scores
    *[f"{p}_rolling_avg" for p in SCORE_PARAMS],
    # 8 rolling std devs
    *[f"{p}_rolling_std" for p in SCORE_PARAMS],
    # 8 deltas
    *[f"{p}_delta" for p in SCORE_PARAMS],
]


def trapezoidal_score(value: float, ideal_min: float, ideal_max: float,
                      accept_min: float, accept_max: float) -> float:
    """
    Trapezoidal tolerance scoring (0-1 scale).
    - Within [ideal_min, ideal_max]  -> 1.0
    - Linearly drops to 0 at accept_min / accept_max
    - Outside acceptable range       -> 0.0
    """
    if ideal_min <= value <= ideal_max:
        return 1.0
    elif accept_min <= value < ideal_min:
        return (value - accept_min) / (ideal_min - accept_min)
    elif ideal_max < value <= accept_max:
        return (accept_max - value) / (accept_max - ideal_max)
    else:
        return 0.0


class FarmConditionScorer:
    """
    Crop-agnostic scorer.
    Normalizes raw sensor values using the crop profile, then predicts
    the score using the trained model.
    """

    def __init__(self, model_path: str = "model.pkl",
                 profile_path: str = "crop_profiles.json"):
        self.model = joblib.load(model_path)

        with open(profile_path, "r") as f:
            self.profiles = json.load(f)

        # Load feature importance if available
        feat_meta_path = str(Path(model_path).with_suffix(".features.json"))
        if Path(feat_meta_path).exists():
            with open(feat_meta_path, "r") as f:
                self.feature_meta = json.load(f)
        else:
            self.feature_meta = None

        print(f"Scorer initialized: model='{model_path}', profiles='{profile_path}'")
        print(f"  Available crops: {list(self.profiles.keys())}")

    def normalize_reading(self, reading: dict, profile: dict) -> dict:
        """
        Normalize a single raw reading to 0-1 scores using the crop's profile.
        """
        params = profile["parameters"]
        normalized = {}
        for sensor, score_name in zip(SENSOR_PARAMS, SCORE_PARAMS):
            cfg = params.get(sensor, {})
            raw_val = reading.get(sensor, 0.0)
            normalized[score_name] = trapezoidal_score(
                raw_val,
                cfg.get("ideal_min", 0),
                cfg.get("ideal_max", 100),
                cfg.get("accept_min", 0),
                cfg.get("accept_max", 100),
            )
        return normalized

    def engineer_features(self, readings: list[dict],
                          profile: dict) -> pd.DataFrame:
        """
        Build the 32-feature vector from a list of readings.
        readings[0] = most recent, readings[-1] = oldest.

        1. Normalize each reading to 0-1 scores using the crop profile
        2. Compute rolling avg, std, delta from the normalized scores
        """
        if not readings:
            raise ValueError("No readings provided")

        # Normalize all readings
        normalized_readings = [self.normalize_reading(r, profile) for r in readings]

        current = normalized_readings[-1]  # Most recent is LAST element
        features = {}

        # Current normalized scores
        for sp in SCORE_PARAMS:
            features[sp] = current[sp]

        if len(normalized_readings) >= 2:
            # Build history array for each normalized score
            for sp in SCORE_PARAMS:
                values = np.array([nr[sp] for nr in normalized_readings])
                features[f"{sp}_rolling_avg"] = float(np.mean(values))
                features[f"{sp}_rolling_std"] = float(np.std(values))
                features[f"{sp}_delta"] = features[sp] - features[f"{sp}_rolling_avg"]
        else:
            # Cold start: only 1 reading
            for sp in SCORE_PARAMS:
                features[f"{sp}_rolling_avg"] = features[sp]
                features[f"{sp}_rolling_std"] = 0.0
                features[f"{sp}_delta"] = 0.0

        df = pd.DataFrame([features])[FEATURE_COLUMNS]
        return df

    def compute_trend(self, current_score: float, avg_score: float,
                      std_score: float) -> str:
        """Determine trend direction. Higher score = closer to ideal."""
        delta = current_score - avg_score
        threshold = max(std_score * 0.3, 0.01)

        if delta > threshold:
            return "improving"
        elif delta < -threshold:
            return "degrading"
        return "stable"

    def predict_score(self, readings: list[dict], crop_id: str) -> dict:
        """
        Predict the farm condition score from recent readings.

        Works for ANY crop in crop_profiles.json.

        Args:
            readings: List of sensor data dicts, newest first.
                      Each dict has raw keys: soil_moisture, soil_temp, etc.
            crop_id: Crop profile ID (e.g., "POTATO_001", "WHEAT_001")

        Returns:
            Score response dict with overall score, per-parameter details, trends.
        """
        if crop_id not in self.profiles:
            raise ValueError(
                f"Unknown crop_id: '{crop_id}'. "
                f"Available: {list(self.profiles.keys())}"
            )

        profile = self.profiles[crop_id]

        # Engineer normalized features
        features_df = self.engineer_features(readings, profile)

        # Model predicts the score
        predicted_score = float(self.model.predict(features_df)[0])
        predicted_score = round(max(0.0, min(100.0, predicted_score)), 1)

        # Per-parameter details with trends
        current = readings[-1]  # The NEWEST reading (appended last)
        current_normalized = self.normalize_reading(current, profile)

        per_parameter = {}
        for sensor, score_name in zip(SENSOR_PARAMS, SCORE_PARAMS):
            raw_val = current.get(sensor, 0.0)
            current_score = current_normalized[score_name]
            avg_score = float(features_df[f"{score_name}_rolling_avg"].iloc[0])
            std_score = float(features_df[f"{score_name}_rolling_std"].iloc[0])

            # Trend
            if len(readings) < 2:
                trend = "stable"
            else:
                trend = self.compute_trend(current_score, avg_score, std_score)

            # Feature contribution (from model's feature importance)
            contribution = None
            if self.feature_meta and "feature_importance" in self.feature_meta:
                contribution = self.feature_meta["feature_importance"].get(score_name, 0.0)

            param_cfg = profile["parameters"].get(sensor, {})
            per_parameter[sensor] = {
                "value": round(raw_val, 2),
                "normalized_score": round(current_score, 3),
                "rolling_avg": round(avg_score, 3),
                "trend": trend,
                "contribution": contribution,
            }

        # Build ideal ranges for response
        ideal_ranges = {}
        for sensor in SENSOR_PARAMS:
            cfg = profile["parameters"].get(sensor, {})
            ideal_ranges[sensor] = {
                "ideal_min": cfg.get("ideal_min"),
                "ideal_max": cfg.get("ideal_max"),
                "accept_min": cfg.get("accept_min"),
                "accept_max": cfg.get("accept_max"),
            }

        return {
            "crop_id": crop_id,
            "crop_name": profile.get("name", crop_id),
            "predicted_score": predicted_score,
            "per_parameter": per_parameter,
            "ideal_ranges": ideal_ranges,
            "readings_used": len(readings),
            "data_timestamp": readings[0].get("timestamp", None),
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
