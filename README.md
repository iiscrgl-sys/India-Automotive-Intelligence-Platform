# India Automotive Intelligence Platform (IAIP)

**IISc DA 231o · Data Engineering at Scale · Team The Quants**

A big-data pipeline on India's new-vehicle registrations (VAHAN, Ministry of Road Transport & Highways) and road-safety statistics (MoRTH), from raw government files to an interactive dashboard.

## What is in this repository

This repository holds the **Streamlit dashboard** and a copy of the **Gold layer** it reads:

| Path | Contents |
|---|---|
| `app.py` | the dashboard (7 pages) |
| `data/gold/` | Gold tables: star-schema facts/dimensions, Spark SQL views, MLlib results |
| `data/silver/`, `data/stream/` | data-quality report and Kafka streaming log |
| `data/reports/` | E1 scalability and E3 data-quality test results |

## Pipeline

```
VAHAN + MoRTH files ─► Bronze ─► Silver ─► Gold ─► Streamlit dashboard / Power BI
 (88 raw files)        raw,      cleaned,   star schema       ▲
                       lineage   checked    + Spark SQL views │
                                                 ▲            │
        monthly refresh: producer ─► Kafka ─► Spark Structured Streaming (upsert)
```

- **Spark (PySpark 4.2)** medallion layers in Parquet, fact table partitioned by year × state
- **Kafka + Spark Structured Streaming** monthly refresh with quarantine of bad records
- **Spark MLlib**: next-month EV-share forecast (linear regression, random forest, GBT vs baselines) and KMeans state groups

## Results

| Test | Result |
|---|---|
| E1 · Scalability | linear in data size (4× data → 3.8× time, 23.6 M rows in 30 s); 4.9× speed-up on 8 cores |
| E2 · Streaming refresh | idempotent replay; Kafka → Gold update in about 25 s |
| E3 · Data quality | 450 / 450 injected errors caught (9 kinds), 0 false alarms; 41 / 41 Silver checks |
| E4 · Machine learning | forecast RMSE 3.09 pp on 2026, 51% lower than the same-month-last-year baseline; 5 state groups |
| E5 · Dashboard | render time of every page is measured live (timer in the sidebar), target under 3 s |

## Data sources

- VAHAN Public Report, Ministry of Road Transport & Highways, Government of India: <https://analytics.parivahan.gov.in/analytics/publicdashboard/vahan>
- Road Accidents in India 2023 and state-wise accident data, MoRTH / Open Government Data Platform India

Registration data: January 2020 to the latest download (the latest month is partial). Road-safety data: 2019–2023.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```
