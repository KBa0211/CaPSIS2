import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_DATA_PATH = BASE_DIR / "data" / "cleaned_data.csv"
DB_PATH = BASE_DIR / "data" / "output.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS earthquakes (
    event_id TEXT PRIMARY KEY,
    magnitude REAL NOT NULL,
    depth REAL NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    event_type TEXT NOT NULL,
    magnitude_type TEXT NOT NULL,
    review_status TEXT NOT NULL,
    source_network TEXT NOT NULL,
    event_datetime TEXT NOT NULL,
    last_updated_datetime TEXT NOT NULL,
    update_delay_minutes REAL,
    seismic_energy_joules REAL,
    log10_energy REAL,
    severity_class TEXT,
    depth_zone TEXT,
    place TEXT
);
"""

INSERT_SQL = """
INSERT OR IGNORE INTO earthquakes (
    event_id, magnitude, depth, latitude, longitude,
    event_type, magnitude_type, review_status, source_network,
    event_datetime, last_updated_datetime, update_delay_minutes,
    seismic_energy_joules, log10_energy, severity_class, depth_zone, place
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

def insert_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    rows = list(df.itertuples(index=False, name=None))
    with conn:
        conn.executemany(INSERT_SQL, rows)
    cursor = conn.execute("SELECT COUNT(*) FROM earthquakes;")
    return int(cursor.fetchone()[0])

def verify_database(conn: sqlite3.Connection) -> Dict[str, Any]:
    total_rows = conn.execute("SELECT COUNT(*) FROM earthquakes;").fetchone()[0]
    duplicate_ids = conn.execute(
        "SELECT COUNT(*) FROM (SELECT event_id FROM earthquakes GROUP BY event_id HAVING COUNT(*) > 1);"
    ).fetchone()[0]

    top_5_df = pd.read_sql_query(
        """
        SELECT event_id, magnitude, depth, source_network, review_status, event_datetime, place
        FROM earthquakes
        ORDER BY magnitude DESC
        LIMIT 5;
        """,
        conn,
    )

    status_counts_df = pd.read_sql_query(
        """
        SELECT review_status, COUNT(*) AS event_count, ROUND(AVG(magnitude), 3) AS avg_mag
        FROM earthquakes
        GROUP BY review_status;
        """,
        conn,
    )

    logging.info("--- SQLite3 Verification Queries ---")
    logging.info("Total rows in earthquakes table: %d | Duplicate event_ids: %d", total_rows, duplicate_ids)
    logging.info("Top 5 strongest earthquakes:\n%s", top_5_df.to_string(index=False))
    logging.info("Counts by review_status:\n%s", status_counts_df.to_string(index=False))

    return {
        "total_rows": int(total_rows),
        "duplicate_ids": int(duplicate_ids),
        "top_5": top_5_df,
        "status_counts": status_counts_df,
    }

def load_to_sqlite(df: Optional[pd.DataFrame] = None, db_path: Path = DB_PATH) -> Dict[str, Any]:
    if df is None:
        if not CLEANED_DATA_PATH.exists():
            raise FileNotFoundError(f"Cleaned data not found at {CLEANED_DATA_PATH}. Run cleaner.py first.")
        df = pd.read_csv(CLEANED_DATA_PATH)

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    try:
        with conn:
            conn.execute(CREATE_TABLE_SQL)

        count_after_run_1 = insert_dataframe(conn, df)
        logging.info("SQLite Load Run #1 complete | Rows in DB: %d", count_after_run_1)

        count_after_run_2 = insert_dataframe(conn, df)
        logging.info("SQLite Load Run #2 (Idempotency Test) complete | Rows in DB: %d", count_after_run_2)

        idempotency_passed = count_after_run_1 == count_after_run_2
        logging.info("Idempotency check passed: %s (diff = %d)", idempotency_passed, count_after_run_2 - count_after_run_1)

        verification = verify_database(conn)
    finally:
        conn.close()

    return {
        "processed_records": len(df),
        "count_run_1": count_after_run_1,
        "count_run_2": count_after_run_2,
        "idempotency_passed": idempotency_passed,
        "verification": verification,
    }

if __name__ == "__main__":
    result = load_to_sqlite()
    print(
        f"Processed: {result['processed_records']} | "
        f"DB Run 1: {result['count_run_1']} | DB Run 2: {result['count_run_2']} | "
        f"Idempotent: {result['idempotency_passed']}"
    )