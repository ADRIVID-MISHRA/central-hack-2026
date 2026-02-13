"""
FastAPI Application for Farm Condition Matching AI.

Provides REST endpoints for the predicted farm condition score.
Continuously polls MongoDB every 10s for NEW readings only,
maintains a sliding window in memory, and updates the cached score.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from collections import deque

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from db import db
from scorer import FarmConditionScorer


# --- State ---
latest_score: dict = None
score_history: deque = deque(maxlen=100)  # Last 100 computed scores
scorer: FarmConditionScorer = None
polling_task: asyncio.Task = None

# Sliding window of recent readings (oldest → newest)
reading_window: deque = deque(maxlen=settings.history_window)
last_seen_timestamp: str = None


async def poll_and_score():
    """
    Background loop: every 10s, fetch ONLY NEW readings from DB,
    append them to the sliding window, and re-predict the score.
    """
    global latest_score, last_seen_timestamp

    # --- Seed: fetch ALL existing readings at once to bootstrap ---
    try:
        all_readings = await db.get_all_readings(crop_id=settings.crop_id)
        if all_readings:
            for r in all_readings:
                reading_window.append(r)  # deque(maxlen) auto-trims old ones
            last_seen_timestamp = all_readings[-1].get("timestamp")
            # Score the full window
            result = scorer.predict_score(
                list(reading_window), settings.crop_id
            )
            latest_score = result
            score_history.append(result)
            print(
                f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                f"SEED: loaded {len(all_readings)} readings → "
                f"score={result['predicted_score']} "
                f"(window={len(reading_window)})"
            )
        else:
            print(
                f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                f"No readings found for crop '{settings.crop_id}'"
            )
    except Exception as e:
        print(f"[Seed error] {e}")

    # --- Continuous polling ---
    while True:
        await asyncio.sleep(settings.poll_interval_seconds)

        try:
            if last_seen_timestamp is None:
                # Still no data — try the latest again
                seed = await db.get_latest_reading(
                    crop_id=settings.crop_id
                )
                if seed:
                    reading_window.append(seed)
                    last_seen_timestamp = seed.get("timestamp")
                else:
                    print(
                        f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                        f"Still no data for '{settings.crop_id}'"
                    )
                    continue

            # Fetch only readings newer than the last one we saw
            new_readings = await db.get_new_readings_since(
                since_timestamp=last_seen_timestamp,
                crop_id=settings.crop_id,
            )

            if new_readings:
                for r in new_readings:
                    reading_window.append(r)
                # Update cursor to newest timestamp
                last_seen_timestamp = new_readings[-1].get("timestamp")

                # Re-score with the updated window
                readings_list = list(reading_window)
                result = scorer.predict_score(
                    readings_list, settings.crop_id
                )
                latest_score = result
                score_history.append(result)
                print(
                    f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                    f"+{len(new_readings)} new → "
                    f"score={result['predicted_score']} "
                    f"(window={len(reading_window)})"
                )
            else:
                print(
                    f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                    f"0 new readings (window={len(reading_window)})"
                )

        except Exception as e:
            print(f"[Poll error] {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global scorer, polling_task

    # Startup
    await db.connect()
    scorer = FarmConditionScorer(
        model_path=settings.model_path,
        profile_path=settings.profile_path,
    )
    polling_task = asyncio.create_task(poll_and_score())
    print(
        f"Polling started: every {settings.poll_interval_seconds}s "
        f"for crop '{settings.crop_id}' "
        f"(window={settings.history_window})"
    )

    yield

    # Shutdown
    if polling_task:
        polling_task.cancel()
    await db.disconnect()


# --- App ---
app = FastAPI(
    title="Farm Condition Matching AI",
    description="Predicts a 0-100 score for how close farm conditions are to ideal crop growth",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Farm Condition Matching AI",
        "crop_id": settings.crop_id,
        "status": "running",
        "poll_interval": settings.poll_interval_seconds,
        "window_size": settings.history_window,
        "current_window": len(reading_window),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/score")
async def get_score():
    """
    Get the latest predicted farm condition score.

    The score (0-100) is predicted by an ML model using both the
    current sensor reading AND historical trends from past readings.
    The background poller queries only NEW values from the DB every 10s
    and maintains a rolling window in memory.
    """
    if latest_score is None:
        raise HTTPException(
            status_code=503,
            detail="Score not yet available. Waiting for first poll cycle.",
        )
    return latest_score


@app.get("/score/history")
async def get_score_history(limit: int = 20):
    """Get the last N computed scores."""
    if not score_history:
        raise HTTPException(status_code=503, detail="No scores computed yet.")

    items = list(score_history)[-limit:]
    return {
        "crop_id": settings.crop_id,
        "count": len(items),
        "scores": items,
    }


@app.get("/score/now")
async def get_score_now():
    """
    Force an immediate score computation (bypasses poll interval).
    Fetches the latest reading from DB right now, appends it to
    the window, and returns the updated score.
    """
    if scorer is None:
        raise HTTPException(status_code=503, detail="Scorer not initialized.")

    global latest_score, last_seen_timestamp

    # Fetch any new readings since our cursor
    if last_seen_timestamp:
        new_readings = await db.get_new_readings_since(
            since_timestamp=last_seen_timestamp,
            crop_id=settings.crop_id,
        )
        if new_readings:
            for r in new_readings:
                reading_window.append(r)
            last_seen_timestamp = new_readings[-1].get("timestamp")
    else:
        # Cold start — grab the latest
        seed = await db.get_latest_reading(crop_id=settings.crop_id)
        if seed:
            reading_window.append(seed)
            last_seen_timestamp = seed.get("timestamp")

    if not reading_window:
        raise HTTPException(
            status_code=404,
            detail=f"No sensor readings found for crop '{settings.crop_id}'.",
        )

    result = scorer.predict_score(list(reading_window), settings.crop_id)
    latest_score = result
    score_history.append(result)

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
