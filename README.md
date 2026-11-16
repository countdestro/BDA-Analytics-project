# NSE Big Data Analytics

PySpark pipeline and interactive dashboard for the supplied NSE daily Parquet history. The pipeline is built for local Spark on Windows; it does not claim a multi-node Spark or HDFS run.

## Setup

Use Python 3.11 or 3.12 with Java 21. From this project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The raw dataset should be under `dataset/raw/nse/` as year-partitioned Parquet files. The financial sample and official company master are under `dataset/raw/company_master/`.

## Run ETL

```powershell
PowerShell -ExecutionPolicy Bypass -File .\run_project.ps1 etl
```

Outputs are written to `dataset/processed/spark_output/`:

- `prices_clean/`: validated daily observations, partitioned by year, with simple daily returns.
- `stock_summary/`, `yearly_summary/`, `monthly_summary/`, `daily_market_summary/`: dashboard tables.
- `quality_report.json`: rejected-row counts, retained zero-volume rows, runtime, and execution mode.
- `spark_sql_year_series/`: a Spark SQL aggregation result.

The pipeline retains EQ, BE, and BZ; preserves missing optional descriptions; retains zero-volume rows; and rejects missing keys, unsupported series, non-positive OHLC, negative volume/turnover/trades, inconsistent OHLC, and duplicated `(date, symbol, series)` observations. Returns use unadjusted closes. Annualized volatility uses the √252 convention.

`run_project.ps1` sets the project's Hadoop native utilities and uses Windows short paths to avoid Spark launcher problems when the project folder contains spaces.

The matching Hadoop 3.5.0 Windows native utilities are included under `.hadoop-native/`. They were downloaded from the [zehelh/winutils Hadoop 3.5.0 native release](https://github.com/zehelh/winutils/releases/tag/hadoop-3.5.0), built from the Apache Hadoop sources and distributed under Apache License 2.0. The project uses the `winutils.exe` and native Hadoop DLLs to support Spark's local Windows filesystem writes.

### Windows filesystem note

Spark's Hadoop local filesystem may require `winutils.exe`. If Spark fails during output creation with a `HADOOP_HOME` or `winutils.exe` error, configure `HADOOP_HOME` to a Hadoop utilities directory with a version compatible with the Hadoop client bundled with the installed Spark, and make sure `%HADOOP_HOME%\bin` is on `PATH`. The pipeline will otherwise report the actual Spark write error; it does not silently substitute a different output format.

## Run dashboard

After the ETL has produced curated output:

```powershell
PowerShell -ExecutionPolicy Bypass -File .\run_project.ps1 dashboard
```

The six pages are Market Overview, Stock Explorer, Market Trends, Company Fundamentals, Correlation & Risk, and Data Quality & Pipeline. Historical price rows are scanned from the selected Parquet partitions; the app does not load the full history into memory on startup.

Company financials are shown by company name and reporting basis. They are intentionally not joined to NSE price history because no reviewed mapping has been established. Coverage is uneven and missingness is shown.

## Current environment boundary

Spark runs in `local[*]`. No HDFS, YARN, or multi-machine environment is configured in this checkout. HDFS block/replication checks, Spark-on-YARN, cluster performance comparisons, and a reviewed historical security mapping remain follow-up work and must not be reported as completed.
