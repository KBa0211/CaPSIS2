import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Any

from kafka import KafkaConsumer
from kafka.errors import KafkaError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).resolve().parent.parent
CONSUMED_DATA_PATH = BASE_DIR / "data" / "consumed_data.json"

BOOTSTRAP_SERVERS = ["127.0.0.1:9092"]
TOPIC_NAME = "earthquakes_raw"
GROUP_ID = "earthquake-pipeline-group"


def safe_json_deserializer(raw_bytes: bytes) -> Any:
    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logging.error("Deserialization error: %s", exc)
        return None


def consume_messages(
    topic: str = TOPIC_NAME,
    bootstrap_servers: List[str] = BOOTSTRAP_SERVERS,
    group_id: str = GROUP_ID,
    timeout_ms: int = 5000,
) -> List[Dict[str, Any]]:
    try:
        consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=safe_json_deserializer,
        )
    except KafkaError as exc:
        logging.error("Failed to connect Kafka Consumer: %s", exc)
        raise

    consumed_records: List[Dict[str, Any]] = []
    deserialization_errors = 0
    initial_wait_sec = 20.0
    idle_timeout_sec = max(timeout_ms / 1000.0, 3.0)
    start_time = time.monotonic()
    last_msg_time = start_time

    try:
        logging.info("Listening to topic '%s' (timeout=%dms)...", topic, timeout_ms)
        while True:
            records_batch = consumer.poll(timeout_ms=1000)
            if records_batch:
                for messages in records_batch.values():
                    for message in messages:
                        if message.value is None:
                            deserialization_errors += 1
                            continue
                        consumed_records.append(message.value)
                last_msg_time = time.monotonic()
            else:
                now = time.monotonic()
                if consumed_records and (now - last_msg_time) >= idle_timeout_sec:
                    break
                if not consumed_records and (now - start_time) >= initial_wait_sec:
                    break

        if consumed_records:
            consumer.commit()
    except KafkaError as exc:
        logging.error("Error while consuming messages: %s", exc)
        raise
    finally:
        consumer.close()

    CONSUMED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONSUMED_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(consumed_records, f, indent=2)

    logging.info(
        "Kafka Consumer finished | Topic: '%s' | Consumed: %d | Deserialization errors: %d",
        topic,
        len(consumed_records),
        deserialization_errors,
    )
    return consumed_records


if __name__ == "__main__":
    records = consume_messages()
    print(f"Successfully consumed messages: {len(records)}")