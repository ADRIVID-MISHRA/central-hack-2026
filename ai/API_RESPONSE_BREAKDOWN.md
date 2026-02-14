# API Response Breakdown: What's Model vs. Hardcoded?

This document explains exactly how each field in the API response is generated.

## Summary

*   **真正的 AI 模型预测 (The ONLY true AI prediction)**: `predicted_score`
    *   This is the output of the trained machine learning model (Random Forest / XGBoost, etc.).
    *   It takes 32 engineered features (current + history) as input and outputs a single 0-100 score.
*   **确定性逻辑 (Deterministic Math/Logic)**: `normalized_score`, `rolling_avg`, `trend`
    *   These are calculated using standard mathematical formulas in `scorer.py`, NOT the AI model.
    *   `normalized_score`: Uses the trapezoidal function based on crop profile limits.
    *   `trend`: Simple if/else logic comparing current vs average.
*   **硬编码配置 (Hardcoded Config/Metadata)**: `ideal_ranges`, `crop_name`, `contribution`
    *   These come directly from JSON files (`crop_profiles.json`, `model.features.json`).
    *   `contribution`: This is *Global Feature Importance* from the training phase, not a dynamic explanation for *this* specific reading.

---

## Detailed Field Breakdown

### Top-Level Fields

| Field | Source | Explanation |
| :--- | :--- | :--- |
| `predicted_score` | **AI MODEL** | The direct output of `self.model.predict()`. This is the core intelligence. |
| `crop_id` | **Config** | From `settings.crop_id` (e.g., "POTATO_001"). |
| `crop_name` | **Config** | From `crop_profiles.json`. |
| `ideal_ranges` | **Config** | Copied directly from `crop_profiles.json`. |
| `readings_used` | **Input Data** | Simply the count of items in the request list. |

### Per-Parameter Fields (`per_parameter.<sensor>`)

| Field | Source | Explanation |
| :--- | :--- | :--- |
| `value` | **Input Data** | The raw sensor reading passed to the API. |
| `normalized_score` | **Logic** | Calculated via `trapezoidal_score()` function. It maps the raw value to 0-1 based on the crop's ideal/acceptable ranges. It is purely mathematical. |
| `rolling_avg` | **Logic** | Simple mathematical average of the `normalized_score` over the history window. |
| `trend` | **Logic** | A simple heuristic: `if (current - avg) > threshold: "improving"`. |
| `contribution` | **Static Metadata** | Loaded from `model.features.json`. It represents generally how important this feature was during *training*. It does **not** change based on the current input values. |
