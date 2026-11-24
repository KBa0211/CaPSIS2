import logging

logging.getLogger("kafka").setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from src.api_client import fetch_earthquake_data
from src.producer import publish_messages
from src.consumer import consume_messages
from src.validator import validate_consumed_data
from src.cleaner import clean_and_transform
from src.loader import load_to_sqlite
from src.analysis import run_eda

def run_pipeline() -> None:
    print("=" * 70)
    print("  USGS EARTHQUAKE DATA STREAMING & VALIDATION PIPELINE (SIS 2)")
    print("=" * 70)

    print("\n[Stage 1/6] Collecting data from USGS Earthquake Catalog API...")
    raw_records = fetch_earthquake_data(limit=300, days_back=30)
    collected_count = len(raw_records)

    print("\n[Stage 2/6] Streaming records through Apache Kafka...")
    published_count = publish_messages(raw_records)
    consumed_records = consume_messages(timeout_ms=5000)
    consumed_count = len(consumed_records)

    print("\n[Stage 3/6] Validating consumed records with Pandera...")
    validation_res = validate_consumed_data(consumed_records)

    print("\n[Stage 4/6] Cleaning and transforming data with pandas & NumPy...")
    cleaning_res = clean_and_transform(validation_res["valid_df"])

    print("\n[Stage 5/6] Loading data into SQLite3 & testing idempotency...")
    loader_res = load_to_sqlite(cleaning_res["cleaned_df"])

    print("\n[Stage 6/6] Running EDA and generating Matplotlib/Seaborn figures...")
    eda_res = run_eda()

    print("\n" + "=" * 70)
    print("  PIPELINE VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"  1. Collected from USGS API       : {collected_count}")
    print(f"  2. Published to Kafka topic      : {published_count}")
    print(f"  3. Consumed from Kafka topic     : {consumed_count}")
    print(f"  4. Pandera valid records         : {validation_res['valid_count']}")
    print(f"  5. Pandera invalid records       : {validation_res['invalid_count']}")
    print(f"     (Invalid test demo rejected)  : {validation_res['test_summary']['test_invalid']}/{validation_res['test_summary']['test_total']}")
    print(f"  6. Records after cleaning        : {cleaning_res['cleaned_count']} (duplicates removed: {cleaning_res['duplicates_removed']})")
    print(f"  7. SQLite3 rows after Run #1     : {loader_res['count_run_1']}")
    print(f"  8. SQLite3 rows after Run #2     : {loader_res['count_run_2']} (Idempotent: {loader_res['idempotency_passed']})")
    print(f"  9. Figures generated             : {len(eda_res['figures'])}")
    print("=" * 70)

if __name__ == "__main__":
    run_pipeline()