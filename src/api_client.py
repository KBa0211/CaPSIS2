import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw_data.csv"

USGS_API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

def fetch_earthquake_data(limit: int = 300, days_back: int = 30) -> List[Dict[str, Any]]:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)

    params = {
        "format": "geojson",
        "starttime": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": end_time.strftime("%Y-%m-%dT%H:%M:%S"),
        "limit": limit,
        "orderby": "time",
    }

    logging.info("Requesting USGS API: %s | params=%s", USGS_API_URL, params)

    try:
        response = requests.get(USGS_API_URL, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        logging.error("API request failed: %s", exc)
        raise
    except ValueError as exc:
        logging.error("Failed to decode JSON response: %s", exc)
        raise

    features = payload.get("features", [])
    records: List[Dict[str, Any]] = []

    for feature in features:
        props = feature.get("properties") or {}
        geom = feature.get("geometry") or {}
        coords = geom.get("coordinates") or [None, None, None]

        records.append({
            "event_id": feature.get("id"),
            "magnitude": props.get("mag"),
            "depth": coords[2] if len(coords) > 2 else None,
            "latitude": coords[1] if len(coords) > 1 else None,
            "longitude": coords[0] if len(coords) > 0 else None,
            "event_type": props.get("type"),
            "magnitude_type": props.get("magType"),
            "review_status": props.get("status"),
            "source_network": props.get("net"),
            "event_time": props.get("time"),
            "last_updated_time": props.get("updated"),
            "place": props.get("place"),
        })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_raw = pd.DataFrame(records)
    df_raw.to_csv(RAW_DATA_PATH, index=False)

    logging.info("Collected %d records and preserved raw data at %s", len(records), RAW_DATA_PATH)
    return records

if __name__ == "__main__":
    data = fetch_earthquake_data(limit=300)
    print(f"Total collected records: {len(data)}")