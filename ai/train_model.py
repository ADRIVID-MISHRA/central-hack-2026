"""
Model Training for Farm Condition Matching AI.
(Crop-Agnostic Version - trains on normalized features)

Trains an XGBoost regressor on normalized 0-1 scores (not raw sensor values).
The trained model works for ANY crop because it learns deviation patterns.

Run:  python train_model.py
"""

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import argparse

# Normalized feature columns (matching generate_training_data.py)
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
    # 8 deltas (current_score - rolling_avg)
    *[f"{p}_delta" for p in SCORE_PARAMS],
]


def train_model(data_path: str = "training_data.csv",
                model_path: str = "model.pkl",
                test_size: float = 0.2,
                seed: int = 42):
    """Train the crop-agnostic XGBoost model on normalized features."""

    print(f"Loading training data from '{data_path}'...")
    df = pd.read_csv(data_path)
    print(f"  {len(df)} samples, {len(df.columns)} columns")

    # Features and label
    X = df[FEATURE_COLUMNS]
    y = df["score"]

    print(f"  Features: {len(FEATURE_COLUMNS)}")
    print(f"  Score range: {y.min():.1f} - {y.max():.1f} (mean={y.mean():.1f})")

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )
    print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

    # Train XGBoost
    try:
        from xgboost import XGBRegressor
        model = XGBRegressor(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=seed,
            n_jobs=-1,
        )
        model_name = "XGBoost"
    except ImportError:
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(
            n_estimators=300,
            max_depth=5,
            learning_rate=0.1,
            subsample=0.8,
            random_state=seed,
        )
        model_name = "GradientBoosting (sklearn fallback)"

    print(f"\nTraining {model_name}...")
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n  Results on test set:")
    print(f"    MAE:  {mae:.2f}")
    print(f"    RMSE: {rmse:.2f}")
    print(f"    R2:   {r2:.4f}")

    # Feature importance
    importances = model.feature_importances_
    feat_importance = dict(zip(FEATURE_COLUMNS, importances.tolist()))

    # Sort and display top 10
    sorted_feats = sorted(feat_importance.items(), key=lambda x: x[1], reverse=True)
    print(f"\n  Top 10 features:")
    for name, imp in sorted_feats[:10]:
        print(f"    {name:40s}  {imp:.4f}")

    # Save model
    joblib.dump(model, model_path)
    print(f"\nModel saved to '{model_path}'")

    # Save feature metadata
    meta_path = str(Path(model_path).with_suffix(".features.json"))
    meta = {
        "model_type": model_name,
        "features": FEATURE_COLUMNS,
        "feature_importance": feat_importance,
        "metrics": {"mae": mae, "rmse": rmse, "r2": r2},
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "note": "Crop-agnostic model. Features are normalized 0-1 scores, not raw sensor values.",
    }
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Feature metadata saved to '{meta_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train crop-agnostic model")
    parser.add_argument("--data", default="training_data.csv", help="Training data CSV")
    parser.add_argument("--model", default="model.pkl", help="Output model path")
    parser.add_argument("--test-size", type=float, default=0.2, help="Test set fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    train_model(args.data, args.model, args.test_size, args.seed)
