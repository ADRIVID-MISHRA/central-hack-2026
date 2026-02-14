# Farm Condition Matching AI - API Documentation

This API provides endpoints to retrieve the predicted farm condition score based on IoT sensor data.

**Base URL:** `http://<host>:<port>` (Default: `http://localhost:8000`)

---

## Endpoints

### 1. root (`GET /`)
Returns the service status and current configuration including crop ID and polling details.

**Response:**
```json
{
  "service": "Farm Condition Matching AI",
  "crop_id": "POTATO_001",
  "status": "running",
  "poll_interval": 10,
  "window_size": 20,
  "current_window": 5
}
```

### 2. Health Check (`GET /health`)
Checks if the service is running.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-10-27T10:00:00+00:00"
}
```

### 3. Get Latest Score (`GET /score`)
Returns the latest cached prediction. The server polls the database in the background every 10 seconds to update this score.

**Response Schema:**
```json
{
  "crop_id": "POTATO_001",
  "crop_name": "Potato (Winter)",
  "predicted_score": 85.5,
  "per_parameter": {
    "soil_moisture": {
      "value": 45.2,
      "normalized_score": 0.8,
      "rolling_avg": 0.78,
      "trend": "improving",
      "contribution": 0.15
    },
    ...
  },
  "ideal_ranges": {
    "soil_moisture": {
      "ideal_min": 40,
      "ideal_max": 60,
      "accept_min": 30,
      "accept_max": 80
    },
    ...
  },
  "readings_used": 20,
  "data_timestamp": "2023-10-27T10:00:00",
  "scored_at": "2023-10-27T10:00:05.123456+00:00"
}
```

### 4. Get Score History (`GET /score/history`)
Returns a list of the last `N` computed scores.

**Query Parameters:**
- `limit` (int, default=20): Number of scores to return.

**Response:**
```json
{
  "crop_id": "POTATO_001",
  "count": 20,
  "scores": [ ... list of score objects like GET /score ... ]
}
```

### 5. Force Immediate Score (`GET /score/now`)
Bypasses the polling interval and forces an immediate fetch of the latest data from the database to compute a new score.

**Response:** Same as `GET /score`.

---

## Data Definitions

### Score Object
The main data structure returned by `/score` and `/score/now`.

| Field | Type | Description |
| :--- | :--- | :--- |
| `crop_id` | string | ID of the crop profile being used (e.g., "POTATO_001"). |
| `crop_name` | string | Human-readable name of the crop. |
| `predicted_score` | float | The overall condition score (0-100). Higher is better. |
| `per_parameter` | object | Dictionary of sensor parameters with detailed scoring info. |
| `ideal_ranges` | object | Dictionary showing the ideal and acceptable ranges used for scoring. |
| `readings_used` | int | Number of historical readings used in the sliding window for this prediction. |
| `data_timestamp` | string | Timestamp of the most recent sensor reading used. |
| `scored_at` | string | Timestamp when the score was calculated (server time). |

### Parameter Detail Object (`per_parameter.<sensor_name>`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `value` | float | The raw sensor value from the latest reading. |
| `normalized_score` | float | Simple 0-1 score for this single reading based on crop profile. |
| `rolling_avg` | float | Rolling average of the normalized score over the history window. |
| `trend` | string | "improving", "degrading", or "stable". |
| `contribution` | float | (Optional) Feature importance/contribution to the final model score. |
