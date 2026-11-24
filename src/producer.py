import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from kafka import KafkaProducer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_PATH = BASE_DIR / "data" / "raw_data.csv"

BOOTSTRAP_SERVERS = ["127.0.0.1:9092"]
TOPIC_NAME = "earthquakes_raw"

def load_records_from_csv(path: Path = RAW_DATA_PATH) -> List[Dict[str, Any]]:
    df = pd.read_csv(path)
    df = df.astype(object).where(pd.notnull(df), None)
    return df.to_dict(orient="records")

def publish_messages(
    records: Optional[List[Dict[str, Any]]] = None,
    topic: str = TOPIC_NAME,
    bootstrap_servers: List[str] = BOOTSTRAP_SERVERS,
) -> int:
    if records is None:
        if not RAW_DATA_PATH.exists():
            raise FileNotFoundError(f"Raw data file not found: {RAW_DATA_PATH}. Run api_client.py first.")
        records = load_records_from_csv(RAW_DATA_PATH)

    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=3,
        )
    except KafkaError as exc:
        logging.error("Failed to connect Kafka Producer: %s", exc)
        raise

    sent_count = 0
    failed_count = 0

    try:
        for record in records:
            try:
                future = producer.send(topic, value=record)
                future.get(timeout=10)
                sent_count += 1
            except KafkaError as exc:
                failed_count += 1
                logging.error("Failed to send record %s: %s", record.get("event_id"), exc)

        producer.flush()
    finally:
        producer.close()

    logging.info(
        "Kafka Producer finished | Topic: '%s' | Published: %d | Failed: %d",
        topic,
        sent_count,
        failed_count,
    )
    return sent_count

if __name__ == "__main__":
    published = publish_messages()
    print(f"Successfully published messages: {published}")