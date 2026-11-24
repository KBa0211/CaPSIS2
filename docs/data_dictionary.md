# Data Dictionary - USGS Earthquake Streaming Pipeline

## Source Dataset
- **API:** USGS Earthquake Catalog API (FDSN Event Web Service)
- **Endpoint:** `https://earthquake.usgs.gov/fdsnws/event/1/query`
- **Format:** GeoJSON

## Raw & Validated Fields (Collected from USGS API)

| Field Name | Data Type | Category | Description | Validation Rule (Pandera) |
| :--- | :--- | :--- | :--- | :--- |
| `event_id` | `TEXT` (`str`) | Identifier | Unique USGS event identifier (e.g., `us6000ud6h`) | Non-null, unique string |
| `magnitude` | `REAL` (`float`) | Numerical | Earthquake magnitude on seismic scale | Non-null, `[-2.0, 10.0]` |
| `depth` | `REAL` (`float`) | Numerical | Hypocenter depth in kilometers (km) | Non-null, `[-10.0, 1000.0]` |
| `latitude` | `REAL` (`float`) | Numerical | Geographic latitude in decimal degrees | Non-null, `[-90.0, 90.0]` |
| `longitude` | `REAL` (`float`) | Numerical | Geographic longitude in decimal degrees | Non-null, `[-180.0, 180.0]` |
| `event_type` | `TEXT` (`str`) | Categorical | Type of seismic event (e.g., `earthquake`, `quarry blast`) | String, nullable |
| `magnitude_type` | `TEXT` (`str`) | Categorical | Method used to calculate magnitude (`ml`, `md`, `mb`, `mw`) | String, nullable |
| `review_status` | `TEXT` (`str`) | Categorical | Human/system review status of the event | Non-null, in `["automatic", "reviewed", "deleted"]` |
| `source_network` | `TEXT` (`str`) | Categorical | Contributing seismic network code (`us`, `ak`, `nc`, `ci`, etc.) | Non-null string |
| `event_time` | `INTEGER` (`ms`) | Date/Time | Event origin time in Unix epoch milliseconds (UTC) | Non-null, `> 0` |
| `last_updated_time` | `INTEGER` (`ms`) | Date/Time | Last metadata update time in Unix epoch milliseconds (UTC) | Non-null, `> 0`, `>= event_time` |
| `place` | `TEXT` (`str`) | Text | Human-readable geographic region description | String, nullable |

## Engineered & Cleaned Fields (Stored in SQLite3 `earthquakes` Table)

| Field Name | Data Type | Description |
| :--- | :--- | :--- |
| `event_datetime` | `TEXT` (UTC ISO) | Converted UTC timestamp (`YYYY-MM-DD HH:MM:SS`) from `event_time` |
| `last_updated_datetime` | `TEXT` (UTC ISO) | Converted UTC timestamp (`YYYY-MM-DD HH:MM:SS`) from `last_updated_time` |
| `update_delay_minutes` | `REAL` | Time elapsed in minutes between `event_datetime` and `last_updated_datetime` |
| `seismic_energy_joules` | `REAL` | Estimated released seismic energy via Gutenberg-Richter formula $E = 10^{1.5M + 4.8}$ (NumPy) |
| `log10_energy` | `REAL` | Base-10 logarithm of estimated seismic energy ($\log_{10} E$) |
| `severity_class` | `TEXT` | Categorical severity band (`micro`, `minor`, `light`, `moderate_or_strong`) |
| `depth_zone` | `TEXT` | Depth classification (`shallow` < 70 km, `intermediate` 70-300 km, `deep` >= 300 km) |