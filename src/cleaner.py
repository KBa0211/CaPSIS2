import logging
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
VALIDATED_DATA_PATH = BASE_DIR / "data" / "validated_data.csv"
CLEANED_DATA_PATH = BASE_DIR / "data" / "cleaned_data.csv"

def clean_and_transform(df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    if df is None:
        if not VALIDATED_DATA_PATH.exists():
            raise FileNotFoundError(f"Validated data not found at {VALIDATED_DATA_PATH}. Run validator.py first.")
        df = pd.read_csv(VALIDATED_DATA_PATH)
    else:
        df = df.copy()

    initial_count = len(df)
    missing_before = df.isnull().sum().to_dict()
    logging.info("Starting cleaning on %d records | Missing values before: %s", initial_count, missing_before)

    duplicates_removed = int(df.duplicated(subset=["event_id"]).sum())
    df = df.drop_duplicates(subset=["event_id"], keep="first").reset_index(drop=True)

    df["event_type"] = df["event_type"].fillna("unknown")
    df["magnitude_type"] = df["magnitude_type"].fillna("unknown")
    df["place"] = df["place"].fillna("unspecified location")
    df = df.dropna(subset=["event_id", "magnitude", "depth", "latitude", "longitude", "event_time"])

    numeric_cols = ["magnitude", "depth", "latitude", "longitude"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    df["event_datetime"] = pd.to_datetime(df["event_time"], unit="ms", utc=True)
    df["last_updated_datetime"] = pd.to_datetime(df["last_updated_time"], unit="ms", utc=True)
    df["update_delay_minutes"] = (
        (df["last_updated_datetime"] - df["event_datetime"]).dt.total_seconds() / 60.0
    ).round(2)

    for col in ["event_type", "magnitude_type", "review_status", "source_network"]:
        df[col] = df[col].astype(str).str.strip().str.lower()
    df["place"] = df["place"].astype(str).str.strip()

    mag_array = df["magnitude"].to_numpy(dtype=float)
    depth_array = df["depth"].to_numpy(dtype=float)

    energy_joules = np.power(10.0, 1.5 * mag_array + 4.8)
    df["seismic_energy_joules"] = np.round(energy_joules, 2)
    df["log10_energy"] = np.round(np.log10(energy_joules), 3)

    mag_conditions = [
        mag_array < 2.0,
        (mag_array >= 2.0) & (mag_array < 4.0),
        (mag_array >= 4.0) & (mag_array < 5.0),
        mag_array >= 5.0,
    ]
    mag_choices = ["micro", "minor", "light", "moderate_or_strong"]
    df["severity_class"] = np.select(mag_conditions, mag_choices, default="unknown")

    depth_conditions = [
        depth_array < 70.0,
        (depth_array >= 70.0) & (depth_array < 300.0),
        depth_array >= 300.0,
    ]
    depth_choices = ["shallow", "intermediate", "deep"]
    df["depth_zone"] = np.select(depth_conditions, depth_choices, default="unknown")

    df = df[(df["event_type"] == "earthquake") & (df["magnitude"].notna()) & (df["depth"] >= -10.0)].copy()

    shallow_notable_df = df[
        (df["magnitude"] >= 2.0) & (df["depth"] < 70.0) & (df["review_status"].isin(["reviewed", "automatic"]))
    ]
    logging.info(
        "Multi-condition filter (mag >= 2.0 & depth < 70km): %d matching events out of %d",
        len(shallow_notable_df),
        len(df),
    )

    network_summary = (
        df.groupby("source_network", as_index=False)
        .agg(
            event_count=("event_id", "count"),
            avg_magnitude=("magnitude", "mean"),
            max_magnitude=("magnitude", "max"),
            avg_depth_km=("depth", "mean"),
        )
        .sort_values(by="event_count", ascending=False)
        .round(3)
    )
    logging.info("GroupBy source_network (top 10):\n%s", network_summary.head(10).to_string(index=False))

    pivot_mag = pd.pivot_table(
        df,
        index="source_network",
        columns="review_status",
        values="magnitude",
        aggfunc="mean",
        fill_value=0.0,
    ).round(3)
    logging.info("Pivot Table (mean magnitude by source_network x review_status):\n%s", pivot_mag.to_string())

    df["event_datetime"] = df["event_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
    df["last_updated_datetime"] = df["last_updated_datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")

    final_columns = [
        "event_id",
        "magnitude",
        "depth",
        "latitude",
        "longitude",
        "event_type",
        "magnitude_type",
        "review_status",
        "source_network",
        "event_datetime",
        "last_updated_datetime",
        "update_delay_minutes",
        "seismic_energy_joules",
        "log10_energy",
        "severity_class",
        "depth_zone",
        "place",
    ]
    df = df[final_columns].reset_index(drop=True)

    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CLEANED_DATA_PATH, index=False)
    logging.info(
        "Cleaning complete | Initial: %d | Duplicates removed: %d | Final cleaned: %d",
        initial_count,
        duplicates_removed,
        len(df),
    )

    return {
        "cleaned_df": df,
        "initial_count": initial_count,
        "duplicates_removed": duplicates_removed,
        "cleaned_count": len(df),
        "filtered_notable_count": len(shallow_notable_df),
        "network_summary": network_summary,
        "pivot_table": pivot_mag,
    }

if __name__ == "__main__":
    res = clean_and_transform()
    print(f"Cleaned records ready for SQLite: {res['cleaned_count']}")