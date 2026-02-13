"""
Synthetic Training Data Generator for Farm Condition Matching AI.
(Crop-Agnostic Version)

Generates labelled training data from ALL crop profiles by:
1. Sampling sensor values across full ranges for EACH crop
2. Normalizing values to 0-1 scores using each crop's trapezoidal ranges
3. Adding temporal features (rolling avg, std, delta of NORMALIZED scores)
4. Computing ground-truth composite score with interaction penalties
5. Outputting training_data.csv with 32 normalized features + label

The model trained on this data works for ANY crop — just add a profile to
crop_profiles.json.

Run:  python generate_training_data.py
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
import argparse


def load_all_profiles(profile_path: str) -> dict:
    """Load all crop profiles from JSON."""
    with open(profile_path, "r") as f:
        return json.load(f)


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


def normalize_sample(sample: dict, profile: dict) -> dict:
    """
    Normalize raw sensor values to 0-1 scores using the crop's profile.
    Returns a dict with keys like soil_moisture_score, soil_temp_score, etc.
    """
    params = profile["parameters"]
    normalized = {}
    for name, cfg in params.items():
        raw_val = sample.get(name, 0)
        normalized[f"{name}_score"] = trapezoidal_score(
            raw_val, cfg["ideal_min"], cfg["ideal_max"],
            cfg["accept_min"], cfg["accept_max"]
        )
    return normalized


def compute_composite_score(normalized: dict, sample: dict) -> float:
    """
    Compute the final 0-100 score from normalized per-parameter scores.
    Includes interaction penalties for dangerous parameter combinations.

    `normalized` has keys like soil_moisture_score (0-1).
    `sample` has raw sensor values for computing interaction thresholds.
    """
    # Average of all normalized scores (each 0-1) -> 0-100
    score_keys = [k for k in normalized.keys() if k.endswith("_score")]
    base_score = sum(normalized[k] for k in score_keys) / len(score_keys) * 100

    # --- Interaction penalties (using RAW values for physical thresholds) ---
    penalty = 0.0

    # High soil temp + low soil moisture = severe stress
    if sample.get("soil_temp", 15) > 25 and sample.get("soil_moisture", 60) < 45:
        severity = ((sample["soil_temp"] - 25) / 10) * ((45 - sample["soil_moisture"]) / 30)
        penalty += min(severity * 15, 15)

    # High air temp + low humidity = desiccation risk
    if sample.get("air_temp", 20) > 30 and sample.get("humidity", 60) < 45:
        severity = ((sample["air_temp"] - 30) / 10) * ((45 - sample["humidity"]) / 30)
        penalty += min(severity * 10, 10)

    # Extreme pH + high nitrogen = nutrient lockout
    if (sample.get("ph", 6.0) < 5.0 or sample.get("ph", 6.0) > 7.0) and sample.get("nitrogen", 150) > 220:
        penalty += 8

    # Low sunlight + high moisture = fungal disease risk
    if sample.get("sunlight", 700) < 300 and sample.get("soil_moisture", 60) > 85:
        penalty += 7

    # Poor air quality + high humidity = pest/disease amplifier
    if sample.get("air_quality", 50) > 200 and sample.get("humidity", 60) > 80:
        penalty += 5

    final_score = max(0.0, min(100.0, base_score - penalty))
    return round(final_score, 2)


def generate_samples_for_crop(profile: dict, n_samples: int,
                               rng: np.random.Generator) -> pd.DataFrame:
    """Generate raw sensor readings for a single crop profile."""
    params = profile["parameters"]
    param_names = list(params.keys())
    data = {}

    for name in param_names:
        cfg = params[name]
        accept_min = cfg["accept_min"]
        accept_max = cfg["accept_max"]
        ideal_min = cfg["ideal_min"]
        ideal_max = cfg["ideal_max"]

        # Wider sampling range: go 30% beyond acceptable bounds
        range_span = accept_max - accept_min
        low = accept_min - 0.3 * range_span
        high = accept_max + 0.3 * range_span

        # 50% from ideal zone, 50% from full range
        n_ideal = n_samples // 2
        n_full = n_samples - n_ideal

        ideal_center = (ideal_min + ideal_max) / 2
        ideal_std = (ideal_max - ideal_min) / 3

        ideal_samples = rng.normal(ideal_center, ideal_std, n_ideal)
        full_samples = rng.uniform(low, high, n_full)

        values = np.concatenate([ideal_samples, full_samples])
        rng.shuffle(values)
        data[name] = values

    # Add cross-parameter correlations
    correlation_noise = rng.normal(0, 3, n_samples)
    temp_deviation = (data["air_temp"] - 20) * 0.5
    data["humidity"] = data["humidity"] - temp_deviation + correlation_noise
    data["soil_temp"] = data["soil_temp"] + (data["air_temp"] - 20) * 0.2 + rng.normal(0, 1, n_samples)

    return pd.DataFrame(data)


# The 8 normalized feature columns the model will use
SCORE_PARAMS = [
    "soil_moisture_score", "soil_temp_score", "air_temp_score",
    "humidity_score", "ph_score", "sunlight_score",
    "nitrogen_score", "air_quality_score",
]


def add_temporal_features(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """
    Simulate temporal features from NORMALIZED scores.
    Creates rolling avg, std, and delta for each normalized score.
    """
    for name in SCORE_PARAMS:
        # Simulate rolling average: current score + small perturbation
        noise_avg = rng.normal(0, 0.08, len(df))
        df[f"{name}_rolling_avg"] = np.clip(df[name] + noise_avg, 0, 1)

        # Simulate rolling std: realistic variability
        df[f"{name}_rolling_std"] = np.abs(rng.normal(0.10, 0.04, len(df)))

        # Delta: current score - rolling avg
        df[f"{name}_delta"] = df[name] - df[f"{name}_rolling_avg"]

    return df


def generate_training_data(profile_path: str = "crop_profiles.json",
                           n_samples_per_crop: int = 20000,
                           output_path: str = "training_data.csv",
                           seed: int = 42) -> pd.DataFrame:
    """
    Full pipeline: generate samples for ALL crops -> normalize -> temporal features -> labels -> save.
    """
    rng = np.random.default_rng(seed)
    all_profiles = load_all_profiles(profile_path)
    crop_ids = list(all_profiles.keys())

    print(f"Generating data for {len(crop_ids)} crops: {crop_ids}")
    print(f"Samples per crop: {n_samples_per_crop}")

    all_dfs = []

    for crop_id in crop_ids:
        profile = all_profiles[crop_id]
        print(f"\n  [{crop_id}] Generating {n_samples_per_crop} raw samples...")

        # 1. Generate raw sensor readings
        raw_df = generate_samples_for_crop(profile, n_samples_per_crop, rng)

        # 2. Normalize each reading using THIS crop's profile
        print(f"  [{crop_id}] Normalizing to 0-1 scores...")
        for _, row in raw_df.iterrows():
            sample = row.to_dict()
            normalized = normalize_sample(sample, profile)
            for k, v in normalized.items():
                raw_df.loc[row.name, k] = v

        # 3. Compute ground-truth score label
        print(f"  [{crop_id}] Computing composite scores...")
        scores = []
        for _, row in raw_df.iterrows():
            sample = {p: row[p] for p in profile["parameters"].keys()}
            normalized = {p: row[p] for p in SCORE_PARAMS}
            score = compute_composite_score(normalized, sample)
            scores.append(score)
        raw_df["score"] = scores

        all_dfs.append(raw_df)

    # Combine all crops
    df = pd.concat(all_dfs, ignore_index=True)

    # Shuffle
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # Keep only normalized score columns (drop raw sensor values)
    keep_cols = SCORE_PARAMS.copy()

    # 4. Add temporal features on normalized scores
    print(f"\nAdding temporal features...")
    df_features = df[keep_cols].copy()
    df_features = add_temporal_features(df_features, rng)

    # Add label
    # Add small noise to labels (real-world isn't perfectly deterministic)
    label_noise = rng.normal(0, 1.5, len(df))
    df_features["score"] = np.clip(df["score"].values + label_noise, 0, 100).round(2)

    # Save
    df_features.to_csv(output_path, index=False)

    total = len(df_features)
    feature_count = len(df_features.columns) - 1
    print(f"\nSaved {total} samples to '{output_path}'")
    print(f"Features: {feature_count} | Label: 'score'")
    print(f"Feature columns: {list(df_features.columns)}")
    print(f"Score distribution: min={df_features['score'].min():.1f}, "
          f"mean={df_features['score'].mean():.1f}, max={df_features['score'].max():.1f}")

    return df_features


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate multi-crop training data (normalized)")
    parser.add_argument("--profile", default="crop_profiles.json", help="Path to crop profiles JSON")
    parser.add_argument("--samples", type=int, default=20000, help="Samples per crop")
    parser.add_argument("--output", default="training_data.csv", help="Output CSV path")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    generate_training_data(args.profile, args.samples, args.output, args.seed)
