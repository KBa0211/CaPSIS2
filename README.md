# Streaming and Validation of Global Earthquake Data: Seismic Activity Analysis Using Apache Kafka and Pandera

**Course:** Data Collection & Preparation (SIS 2)
**Group Members:**
1. Kosherbay Batyrkhan
2. Akhmetova Amina
3. Kyzaybay Balausa
4. Talgat Tastemir

## 1. Project Overview
This project implements an end-to-end Python data pipeline that collects real-world seismic activity records from the public USGS Earthquake Catalog API, streams them as JSON messages through an Apache Kafka Broker, validates records with Pandera (including a 3-record invalid-data test suite), cleans and transforms data using pandas and NumPy, stores processed records idempotently in SQLite3, and produces Exploratory Data Analysis (EDA) statistics and Matplotlib/Seaborn visualizations

## 2. Project Structure
```text
SIS2/
├── docker-compose.yml
├── main.py
├── requirements.txt
├── README.md
├── src/
│   ├── __init__.py
│   ├── api_client.py
│   ├── producer.py
│   ├── consumer.py
│   ├── validator.py
│   ├── cleaner.py
│   ├── loader.py
│   └── analysis.py
├── data/
│   ├── raw_data.csv
│   ├── consumed_data.json
│   ├── validated_data.csv
│   ├── cleaned_data.csv
│   └── output.db
├── figures/
├── docs/
│   └── data_dictionary.md
└── report/
    └── project_report.pdf
```

## 3. Software and Python Requirements
- Python 3.10+ (tested on Python 3.12)
- Docker Desktop (with Docker Compose v2)
- Internet connection for querying the public USGS API (no API key required)

## 4. Dependency Installation
Clone the repository and install all required packages:
```bash
pip install -r requirements.txt
```

## 5. Apache Kafka Broker Setup and Topic Configuration
Start the Apache Kafka 3.7.0 Broker (KRaft mode, port `9092`) via Docker:
```bash
docker compose up -d
```

Verify the broker container is running:
```bash
docker ps
```

Create the Kafka topic `earthquakes_raw` and verify it exists:
```bash
docker exec kafka_broker /opt/kafka/bin/kafka-topics.sh --create --topic earthquakes_raw --bootstrap-server 127.0.0.1:9092 --partitions 1 --replication-factor 1
docker exec kafka_broker /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server 127.0.0.1:9092
```

## 6. API Configuration
- **Source:** USGS Earthquake Catalog API (FDSN Event Web Service)
- **Endpoint:** `https://earthquake.usgs.gov/fdsnws/event/1/query`
- **Parameters:** `format=geojson`, `starttime` (UTC, 30 days prior), `endtime` (current UTC), `limit=300`, `orderby=time`
- **Authentication:** None required (public API)

## 7. Execution Order

### Option A: Run the Complete Pipeline (Recommended)
```bash
python main.py
```

### Option B: Run Each Stage Individually
```bash
python src/api_client.py
python src/producer.py
python src/consumer.py
python src/validator.py
python src/cleaner.py
python src/loader.py
python src/analysis.py
```

## 8. Database Verification and Expected Outputs
After running `python main.py`, verify successful execution by checking:
1. **Terminal summary:** confirms 300 records collected from the USGS API, 300 messages published to `earthquakes_raw`, 300 messages consumed from Kafka, 3/3 deliberately invalid test records rejected by Pandera, cleaned earthquake record count after multi-condition filtering, identical SQLite3 row counts on Run #1 and Run #2 (`Idempotent: True`), and 4 generated figures
2. **SQLite3 database (`data/output.db`):** contains the `earthquakes` table with `event_id TEXT PRIMARY KEY`, 0 duplicate IDs, and printed verification query results (total count, top 5 strongest earthquakes, and review status aggregation)
3. **Generated visualizations (`figures/`):**
   - `magnitude_distribution.png`
   - `depth_vs_magnitude.png`
   - `events_by_network.png`
   - `global_seismic_map.png`

To stop and remove the Kafka container after testing:
```bash
docker compose down
```