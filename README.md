# India Automotive Intelligence Platform (IAIP)

**IISc DA 231o · Data Engineering at Scale · Team The Quants**
Gaurav Agarwal · Arvind Rajput · Subhasis Halder · Arka Ghatak

### 🔗 Live dashboard: **<https://iaip-thequants.streamlit.app/>**

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://iaip-thequants.streamlit.app/)

Works on phone, tablet and PC. If the app has been asleep, click *"Yes, get this app back up!"* and wait about a minute.

### 📊 Power BI dashboard (second dashboard, same Gold layer)

| File | How to open |
|---|---|
| [`IAIP_PowerBI_dashboard.pdf`](IAIP_PowerBI_dashboard.pdf) | opens in any browser or phone (static, 4 pages) |
| [`IAIP_PowerBI.pbix`](IAIP_PowerBI.pbix) | fully interactive: click the file → **Download**, open in **Power BI Desktop** (free, Windows) |

A scalable Spark pipeline that brings India's public vehicle-registration data (VAHAN, Ministry of Road Transport & Highways) and road-safety statistics (MoRTH) into one quality-checked warehouse, refreshes it monthly through Kafka, runs Spark MLlib models on it and serves it through two dashboards.

## Repository layout

| Path | Contents |
|---|---|
| `bronze/` | **raw input data**: 84 VAHAN Public Report extracts + MoRTH road-safety files (88 files) |
| `source_log.csv` | provenance of every raw file: source URL, filters used, download date |
| `notebooks/01_bronze.ipynb` | raw files → Bronze Parquet (all-string schema, lineage, file manifest, structure checks) |
| `notebooks/02_silver.ipynb` | Bronze → Silver (state mapping, numbers, de-duplication, fuel/category/norm groups, maker → brand, 41 quality checks) |
| `notebooks/03_gold.ipynb` | Silver → Gold fact constellation (5 facts, 8 dimensions) and 8 Spark SQL views; Power BI CSV export |
| `notebooks/04_streaming.ipynb` | monthly refresh: producer → Kafka → Spark Structured Streaming (validate, quarantine, upsert partitions) |
| `notebooks/05_mllib.ipynb` | Spark MLlib: next-month EV-share forecast (LR / RF / GBT vs baselines) and KMeans state groups |
| `notebooks/06_quality_and_scale.ipynb` | E3 bad-data injection test and E1 scalability test |
| `streaming/docker-compose.yml` | single-node Kafka (KRaft) used by notebook 04 |
| `dashboard/` | Streamlit app source, local launcher, and `make_deploy.py` which builds the cloud copy |
| `app.py`, `data/`, `requirements.txt` | the deployed Streamlit app and the copy of the Gold layer it reads |
| `reports/` | E1, E3, E5 results (CSV/JSON), charts, final project proposal |

Every notebook is saved **with its outputs**, so the logs, check results and timings of our runs can be read without re-running anything.

## Pipeline

```
VAHAN + MoRTH files ─► Bronze ─► Silver ─► Gold ─► Streamlit dashboard / Power BI
 (88 raw files)        raw,      cleaned,   fact constellation    ▲
                       lineage   checked    + Spark SQL views     │
                                                 ▲                │
        monthly refresh: producer ─► Kafka ─► Spark Structured Streaming (upsert)
```

## How to reproduce

**Requirements:** Python 3.11, Java (JDK) 17, Docker Desktop (for notebook 04 only). Tested on Windows 11, PySpark 4.2.0, 12 logical cores, `local[*]`.

1. Clone or download this repository.
2. `pip install -r requirements-pipeline.txt`
3. Open the `notebooks/` folder in VS Code or Jupyter and run, in order, each notebook top to bottom:
   **01 → 02 → 03** (builds `warehouse/bronze`, `warehouse/silver`, `warehouse/gold`), then **05** (MLlib), **06** (E3 and E1, about 15 minutes).
   The notebooks find the data relative to their own folder (`../bronze`, `../warehouse`), so no paths need editing.
4. **Kafka refresh (04):** start Docker Desktop, then run notebook 04; its first cell starts Kafka from `streaming/docker-compose.yml`.
5. **Dashboard locally:** `cd dashboard` and `python -m streamlit run app.py` (or double-click `run_dashboard.bat` on Windows).
6. **Refresh the cloud copy:** run `dashboard/make_deploy.py`, then upload the `deploy/data` folder to the repository root.

To refresh with newer VAHAN data, re-download the 2026 files with the filters recorded in `source_log.csv`, replace them in `bronze/`, and run notebook 04 (Demo B) followed by 01 → 03.

## Results

| Test | Result |
|---|---|
| E1 · Scalability | linear in data size (4× data → 3.8× time, 23.6 M rows in 30 s); 4.9× speed-up on 8 cores |
| E2 · Streaming refresh | idempotent replay; single change Kafka → Gold in about 25 s; real monthly refresh (4,752 messages: 432 new, 1,288 changed rows) in 43–88 s |
| E3 · Data quality | 450 / 450 injected errors caught (9 kinds), 0 false alarms; 41 / 41 Silver checks |
| E4 · Machine learning | next-month EV-share forecast: RMSE 3.37 pp on Jan–Oct 2026, 47% lower than the same-month-last-year baseline; 5 state groups (KMeans, silhouette 0.40) |
| E5 · Dashboards | Streamlit pages render in 0.15–0.21 s (warm); Power BI visuals in 0.09–0.24 s (DAX 4–11 ms); target under 3 s |

## Data sources and licence

- VAHAN Public Report, Ministry of Road Transport & Highways, Government of India: <https://analytics.parivahan.gov.in/analytics/publicdashboard/vahan>
- State-wise road accidents and deaths, MoRTH / Open Government Data Platform India (data.gov.in); *Road Accidents in India 2023*, MoRTH

All data is public Government of India data, redistributed here unchanged for research and teaching. Registration data: January 2020 to 13 Nov 2026 (the latest month is partial). Road-safety data: 2019–2023.
