import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple

import pandas as pd

try:
    import pandera.pandas as pa
except ImportError:
    import pandera as pa

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
CONSUMED_DATA_PATH = BASE_DIR / "data" / "consumed_data.json"
VALIDATED_DATA_PATH = BASE_DIR / "data" / "validated_data.csv"

def build_earthquake_schema() -> pa.DataFrameSchema:
    return pa.DataFrameSchema(
        columns={
            "event_id": pa.Column(str, nullable=False, unique=True),
            "magnitude": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.in_range(-2.0, 10.0),
            ),
            "depth": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.in_range(-10.0, 1000.0),
            ),
            "latitude": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.in_range(-90.0, 90.0),
            ),
            "longitude": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.in_range(-180.0, 180.0),
            ),
            "review_status": pa.Column(
                str,
                nullable=False,
                checks=pa.Check.isin(["automatic", "reviewed", "deleted"]),
            ),
            "event_time": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.greater_than(0),
            ),
            "last_updated_time": pa.Column(
                float,
                nullable=False,
                coerce=True,
                checks=pa.Check.greater_than(0),
            ),
            "event_type": pa.Column(str, nullable=True),
            "magnitude_type": pa.Column(str, nullable=True),
            "source_network": pa.Column(str, nullable=False),
            "place": pa.Column(str, nullable=True),
        },
        checks=pa.Check(
            lambda df: (df["last_updated_time"] >= df["event_time"]).all(),
            name="updated_after_event",
            error="last_updated_time must be >= event_time",
        ),
        strict=False,
    )

def run_validation(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    schema = build_earthquake_schema()
    df_reset = df.reset_index(drop=True)

    try:
        valid_df = schema.validate(df_reset, lazy=True)
        return valid_df, pd.DataFrame(columns=df_reset.columns), pd.DataFrame()
    except pa.errors.SchemaErrors as exc:
        failure_cases = exc.failure_cases
        invalid_indices = set()
        for idx in failure_cases["index"].dropna().unique():
            try:
                int_idx = int(idx)
                if int_idx in df_reset.index:
                    invalid_indices.add(int_idx)
            except (ValueError, TypeError):
                continue
        invalid_indices = sorted(invalid_indices)
        invalid_df = df_reset.loc[invalid_indices].copy()
        valid_df = df_reset.drop(index=invalid_indices).reset_index(drop=True)
        return valid_df, invalid_df, failure_cases

def run_invalid_test_demo() -> Dict[str, Any]:
    test_records = [
        {
            "event_id": "TEST_INVALID_001",
            "magnitude": 15.5,
            "depth": 10.0,
            "latitude": 43.25,
            "longitude": 76.95,
            "event_type": "earthquake",
            "magnitude_type": "ml",
            "review_status": "reviewed",
            "source_network": "us",
            "event_time": 1700000000000,
            "last_updated_time": 1700000050000,
            "place": "Test Invalid Magnitude",
        },
        {
            "event_id": "TEST_INVALID_002",
            "magnitude": 3.2,
            "depth": 20.0,
            "latitude": 120.0,
            "longitude": 210.0,
            "event_type": "earthquake",
            "magnitude_type": "mb",
            "review_status": "unknown_status",
            "source_network": "ak",
            "event_time": 1700000000000,
            "last_updated_time": 1700000050000,
            "place": "Test Invalid Coords & Status",
        },
        {
            "event_id": "TEST_INVALID_003",
            "magnitude": None,
            "depth": -50.0,
            "latitude": 35.0,
            "longitude": 139.0,
            "event_type": "earthquake",
            "magnitude_type": "mw",
            "review_status": "automatic",
            "source_network": "us",
            "event_time": -100,
            "last_updated_time": 1700000050000,
            "place": "Test Null Mag & Bad Depth",
        },
    ]

    test_df = pd.DataFrame(test_records)
    valid_test, invalid_test, failure_cases = run_validation(test_df)

    logging.info("--- Pandera Validation Test (3 Deliberately Invalid Records) ---")
    logging.info("Test records passed: %d | Test records rejected: %d", len(valid_test), len(invalid_test))
    if not failure_cases.empty:
        logging.info("Detected test errors:\n%s", failure_cases[["column", "check", "failure_case", "index"]].to_string(index=False))
    logging.info("All test records are excluded from the main dataset.")

    return {
        "test_total": len(test_df),
        "test_valid": len(valid_test),
        "test_invalid": len(invalid_test),
        "test_errors_count": len(failure_cases),
    }

def validate_consumed_data(records=None) -> Dict[str, Any]:
    if records is None:
        if not CONSUMED_DATA_PATH.exists():
            raise FileNotFoundError(f"Consumed data not found at {CONSUMED_DATA_PATH}. Run consumer.py first.")
        with open(CONSUMED_DATA_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)

    df = pd.DataFrame(records)
    valid_df, invalid_df, failure_cases = run_validation(df)

    logging.info(
        "Pandera Validation finished | Total: %d | Valid: %d | Invalid: %d",
        len(df),
        len(valid_df),
        len(invalid_df),
    )

    if not invalid_df.empty and not failure_cases.empty:
        logging.warning(
            "Sample real validation errors:\n%s",
            failure_cases[["column", "check", "failure_case", "index"]].head(10).to_string(index=False),
        )

    test_summary = run_invalid_test_demo()

    VALIDATED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    valid_df.to_csv(VALIDATED_DATA_PATH, index=False)
    logging.info("Saved %d validated records to %s", len(valid_df), VALIDATED_DATA_PATH)

    return {
        "valid_df": valid_df,
        "total_input": len(df),
        "valid_count": len(valid_df),
        "invalid_count": len(invalid_df),
        "test_summary": test_summary,
    }

if __name__ == "__main__":
    result = validate_consumed_data()
    print(f"Valid records: {result['valid_count']} | Invalid records: {result['invalid_count']}")