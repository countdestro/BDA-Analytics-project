# NSE Big Data Analytics Platform

## Project blueprint, technical documentation, dashboard specification, and implementation roadmap

**Status:** In progress\
**Main dataset:** Indian NSE daily market data, 2010--2026\
**Processing:** Apache Spark / PySpark\
**Planned distributed storage:** Hadoop HDFS\
**Purpose:** This document records the project goal, datasets,
architecture, Spark and Hadoop learning plan, analytics, detailed
dashboard requirements, current implementation status, known
limitations, and next steps.

------------------------------------------------------------------------

# 1. Project overview

This is an end-to-end Big Data Analytics project for analysing Indian
National Stock Exchange (NSE) equities. It combines historical daily
market data with company reference information and quarterly financial
results.

The goal is to build a reproducible data pipeline, not just a collection
of charts:

1.  Ingest raw market and company data.
2.  Validate, clean, and transform it.
3.  Process millions of daily stock records using Apache Spark.
4.  Store cleaned and aggregated datasets in Parquet.
5.  Learn Hadoop HDFS and integrate it with Spark.
6.  Build analytical datasets and Spark SQL queries.
7.  Calculate returns, volatility, trading activity, and financial
    trends.
8.  Present results in an interactive dashboard.
9.  Document data quality, methodology, limitations, and measured
    performance.

The NSE price dataset currently contains approximately **7.34 million
records** across 17 yearly Parquet files, covering 2010--2026. This is
the principal Big Data component.

## Objectives

-   Demonstrate practical PySpark processing on millions of financial
    records.
-   Build an ETL pipeline with explicit validation and reproducible
    outputs.
-   Learn Spark DataFrames, Spark SQL, partitioning, caching, and
    Parquet.
-   Understand Hadoop HDFS, YARN, and MapReduce concepts.
-   Integrate market prices with company reference data and quarterly
    financials where identifiers match reliably.
-   Produce meaningful financial and market analytics.
-   Build an interactive dashboard backed by curated datasets.
-   Explain the system honestly, including what ran locally versus on a
    distributed cluster.

## Scope boundaries

This is a historical analytics project, not a live trading system or
investment-advice tool. The main price data is daily, not high-frequency
order-book data. The quarterly financial sample is incomplete and
unevenly distributed across companies. The project is not centred on
deep learning or neural networks.

------------------------------------------------------------------------

# 2. Architecture

``` text
                  DATA SOURCES
                       |
          +------------+-------------+
          |            |             |
       NSE daily    NSE equity    Quarterly
       prices       security      financial
                    master        results
          |            |             |
          +------------+-------------+
                       |
                   RAW LAYER
              Original CSV / Parquet
                       |
                       v
                APACHE SPARK
          Read -> Validate -> Clean
          Standardise -> Join -> Derive
                       |
                       v
                PROCESSED LAYER
            Cleaned, partitioned Parquet
                       |
               +-------+-------+
               |               |
               v               v
            Spark SQL      Aggregations
               |               |
               +-------+-------+
                       |
                       v
                ANALYTICS LAYER
        Returns, volatility, liquidity proxies,
        company comparisons, correlations
                       |
                       v
                 DASHBOARD
       Market overview | Stock explorer |
       Trends | Fundamentals | Risk |
       Data quality and pipeline monitoring
```

## Data layers

### Raw

Original downloaded files. Keep these unchanged so that the pipeline can
be rerun and outputs can be traced back to source data.

### Processed

Cleaned, validated, standardised data created by Spark. The price data
is intended to be partitioned by year.

### Curated / analytics

Dashboard-ready tables such as stock summaries, yearly/monthly
summaries, daily market summaries, financial metrics, returns, and
volatility. The dashboard should read these outputs instead of
repeatedly processing all raw records.

------------------------------------------------------------------------

# 3. Data sources and inventory

## 3.1 NSE daily market data

**Source:** Hugging Face dataset `tejhq/indian-markets`\
**Location:** `dataset/raw/nse/`\
**Format:** Parquet\
**Files:** 17 yearly files\
**Coverage:** 2010--2026\
**Rows observed:** 7,342,169

Download command:

``` powershell
hf download tejhq/indian-markets --repo-type dataset --include "nse/**/*.parquet" --local-dir "dataset/raw"
```

### Fields

  Column         Description / use
  -------------- --------------------------------------
  `date`         Trading date
  `symbol`       NSE trading symbol
  `series`       NSE security series
  `isin`         Security identifier, when supplied
  `name`         Company/security name, when supplied
  `open`         Opening price
  `high`         Highest price
  `low`          Lowest price
  `close`        Closing price
  `last`         Last traded price
  `prev_close`   Previous closing price
  `volume`       Traded quantity
  `turnover`     Reported turnover
  `trades`       Number of trades, when supplied
  `year`         Year field / partition
  `month`        Month field

Older records have missing descriptive fields such as ISIN, name, or
trade count. A missing descriptive field should not automatically cause
a valid price record to be discarded.

### Series counts observed

  Series              Records
  ----------- ---------------
  EQ                6,699,579
  BE                  573,959
  BZ                   68,631
  **Total**     **7,342,169**

The current cleaning step retains EQ, BE, and BZ. Do not automatically
classify BE or BZ as non-equities. Determine the intended security
universe using the NSE security reference and, where possible,
historical mappings.

## 3.2 Official NSE equity list

**File:** `dataset/raw/company_master/EQUITY_L.csv`\
**Source:** NSE archives\
**Observed rows:** 2,627\
**Observed series:** EQ, BE, BZ\
**Cleaned output created:** `dataset/processed/company_master.csv`

This is the primary reference for the current equity universe. It is a
current snapshot, not a complete history of all securities listed from
2010 onward.

**Validation still required:** an earlier cleaning step used
`drop_duplicates(subset=["isin"])`. Inspect duplicate ISINs before
treating the result as final. A duplicate identifier may reflect
multiple rows or security records that need investigation rather than
blind deletion.

## 3.3 Additional NSE security master

**Source:** Hugging Face dataset
`tickertruthorg/nse-india-security-master`\
**File:** `dataset/raw/company_master/data/nse_security_master.csv`\
**Rows:** 2,384

Fields:

-   `nse_symbol`
-   `isin`
-   `company_name`
-   `listing_date`
-   `active_flag`

Comparison performed:

  Comparison                                          Count
  ------------------------------------------------- -------
  Official NSE list                                   2,627
  Additional security master                          2,384
  Overlap                                             2,370
  In official list, absent from additional master       257
  In additional master, absent from official list        14

The sources differ. Use the official NSE list as the primary
current-universe reference and the other master as secondary validation.
Investigate mismatches rather than silently deleting them.

## 3.4 Quarterly financial results

**Dataset:** Fliar BI, India Quarterly Results 2019--2026\
**File:**
`dataset/raw/company_master/india_quarterly_results_sample.csv`\
**Shape observed:** 8,039 rows × 19 columns\
**Unique company names:** 1,136\
**Unique exchange codes:** 744\
**Quarter-end range:** 2018-12-31 to 2026-03-31

Fields:

-   `result_id`
-   `company_name`
-   `company_domain`
-   `exchange_code`
-   `sector`
-   `fiscal_year`
-   `quarter`
-   `quarter_end`
-   `basis`
-   `revenue_inr`
-   `net_profit_inr`
-   `ebitda_inr`
-   `revenue_yoy_pct`
-   `net_profit_yoy_pct`
-   `yoy_basis`
-   `revenue_usd`
-   `source`
-   `report_date`
-   `fliar_profile_url`

### Known coverage limitations

-   `basis` is missing in 4,317 rows; 2,419 are consolidated and 1,303
    standalone.
-   EBITDA is missing in 6,406 rows.
-   `net_profit_yoy_pct` is missing in 6,831 rows.
-   No duplicates were found on `[company_name, quarter_end, basis]` in
    the check performed.
-   Only 15 companies have all 30 quarters; 85 have 20 or more; 409 have
    four or fewer.

This is supplementary financial data, not a complete or evenly sampled
financial history. The dashboard must show coverage and missingness.

------------------------------------------------------------------------

# 4. Apache Spark / PySpark

## Why Spark is used

Spark provides distributed-style data processing through partitioned
execution and APIs such as DataFrames and Spark SQL. In this project it
is used to:

-   Read the yearly Parquet files.
-   Inspect schemas and data types.
-   Validate and clean records.
-   Derive date fields and returns.
-   Aggregate by stock, year, month, and trading date.
-   Join reference data where identifiers match reliably.
-   Save cleaned and curated datasets as Parquet.
-   Run analytical SQL queries.

Spark is currently running in local mode. Local Spark is useful for
learning and processing this dataset, but it is not evidence of
multi-machine cluster execution.

## Current environment

  Component   Installed / observed
  ----------- -----------------------------
  Java        OpenJDK 21.0.9 Temurin
  PySpark     4.3.0
  Py4J        0.10.9.9
  PyArrow     26.0.1
  OS          Windows
  Python      Project virtual environment

A Spark session and a simple DataFrame test succeeded.

Current session configuration:

``` python
spark = (
    SparkSession.builder
    .appName("BDA-Stock-Analytics")
    .master("local[*]")
    .config("spark.driver.memory", "6g")
    .config("spark.sql.shuffle.partitions", "12")
    .config("spark.sql.adaptive.enabled", "true")
    .getOrCreate()
)
```

`local[*]` uses the available local CPU cores. Memory and shuffle
settings are initial values, not performance claims.

## Current script and execution

**Script:** `code/processing/nse_spark_analysis.py`

Run from project root:

``` powershell
python code/processing/nse_spark_analysis.py
```

The script currently:

1.  Finds yearly Parquet files recursively.
2.  Reads them into a Spark DataFrame.
3.  Drops records missing essential date, symbol, series, OHLC, or
    volume values.
4.  Retains EQ, BE, and BZ.
5.  Removes records with non-positive close or negative volume.
6.  Caches the cleaned DataFrame.
7.  Computes stock-level aggregations.
8.  Computes yearly aggregations.
9.  Attempts to write cleaned and aggregated Parquet outputs.

The file paths are built using resolved filesystem paths:

``` python
parquet_paths = [file.resolve().as_posix() for file in data_files]
df = spark.read.parquet(*parquet_paths)
```

This fixed an earlier issue involving URL-encoded `=` characters in
partition folder names.

## Current cleaning logic

``` python
df_clean = df.dropna(
    subset=[
        "date", "symbol", "series",
        "open", "high", "low", "close", "volume"
    ]
)

df_clean = df_clean.filter(
    col("series").isin("EQ", "BE", "BZ")
)

df_clean = df_clean.filter(
    (col("close") > 0) & (col("volume") >= 0)
)

df_clean = df_clean.cache()
```

This is an initial cleaning pass, not the final data-quality framework.

### Validation to add

-   Parse `date` to a proper date type.
-   Check `high >= low`.
-   Check `high >= open` and `high >= close`.
-   Check `low <= open` and `low <= close`.
-   Detect duplicate `(date, symbol, series)` observations.
-   Validate turnover and trade counts.
-   Investigate zero-volume records rather than automatically deleting
    them.
-   Preserve records with missing non-essential descriptive fields.
-   Investigate symbol changes and historical identifiers.
-   Confirm turnover units from the source documentation.

## Latest confirmed run

  -----------------------------------------------------------------------
  Stage                               Result
  ----------------------------------- -----------------------------------
  Find 17 yearly files                Successful

  Start Spark 4.3.0                   Successful

  Read full NSE dataset               Successful

  Apply current cleaning              Successful

  Rows after cleaning                 7,342,169

  Stock-wise aggregation              Passed the earlier
                                      unresolved-column issue

  Write Parquet outputs               Failed due to Windows Hadoop
                                      filesystem setup
  -----------------------------------------------------------------------

### Current Windows issue

The latest failure is during filesystem/output handling, not the earlier
Python aggregation-column bug. Logs include:

``` text
HADOOP_HOME and hadoop.home.dir are unset
winutils.exe missing
```

There were also Windows Hadoop native filesystem warnings, including
`NativeIO$Windows.access0`.

### Environment decision still pending

Recommended option: move the Spark/Hadoop development environment to
**WSL2 Ubuntu**. This avoids spending excessive time on Windows native
Hadoop filesystem compatibility and gives a Linux-like environment
closer to common data-engineering deployments.

This migration has not yet been confirmed. The alternative is to
continue fixing native Windows support. Do not assume WSL2 is already
installed or configured.

------------------------------------------------------------------------

# 5. Hadoop learning and Spark integration

Spark and Hadoop are related technologies, but they are not
interchangeable.

## HDFS

Hadoop Distributed File System is designed to store large files across
multiple machines.

Concepts to learn:

-   **NameNode:** Maintains filesystem metadata and namespace.
-   **DataNode:** Stores data blocks.
-   **Blocks:** Large files are split into blocks for storage.
-   **Replication:** Blocks can be stored on multiple DataNodes for
    fault tolerance.
-   **Rack awareness:** Placement can account for network topology.
-   **High availability:** Helps reduce dependence on a single NameNode.

## YARN

YARN is Hadoop's resource-management and job-scheduling layer.

Learn:

-   ResourceManager.
-   NodeManager.
-   ApplicationMaster.
-   Containers.
-   Resource allocation and scheduling.

## MapReduce

MapReduce is Hadoop's distributed batch-processing model:

1.  Map phase.
2.  Shuffle and sort.
3.  Reduce phase.

The project does not need to be rewritten as a MapReduce application.
The purpose is to understand how this model works and how Spark's
execution model differs.

## Spark versus Hadoop

  -----------------------------------------------------------------------
  Topic                   Spark                   Hadoop
  ----------------------- ----------------------- -----------------------
  Project role            Processing and          Distributed storage and
                          analytics               ecosystem

  Processing              DataFrames, SQL, RDDs   MapReduce and other
                                                  engines

  Storage                 Reads/writes local,     HDFS is a core storage
                          cloud, HDFS and other   component
                          sources                 

  SQL                     Spark SQL               Often supplied through
                                                  tools such as Hive

  Resource management     Standalone, Kubernetes, YARN is common
                          YARN, etc.              
  -----------------------------------------------------------------------

Spark can run without HDFS. It currently runs locally and can use the
local filesystem. HDFS is a later integration stage.

## Planned Spark--HDFS architecture

``` text
NSE source files
      |
      v
HDFS raw zone
      |
      v
Spark reads from HDFS
      |
      v
Spark ETL and analytics
      |
      v
HDFS processed / curated zones
      |
      v
Spark SQL / dashboard access
```

Learning sequence:

1.  Learn HDFS architecture and basic filesystem commands.
2.  Set up a small Hadoop environment.
3.  Upload a sample NSE dataset to HDFS.
4.  Inspect blocks and replication.
5.  Configure Spark to read from HDFS.
6.  Run a Spark transformation and write output back to HDFS.
7.  Compare local and HDFS workflows.
8.  Explore Spark on YARN after the basic integration works.

Do not introduce HDFS, YARN, Hive, Kafka, and multiple cluster managers
simultaneously. First build one working Spark--HDFS integration.

------------------------------------------------------------------------

# 6. Analytics and methodology

## Price returns

For closing price (P_t):

**Daily simple return**

\[ R_t = `\frac{P_t}{P_{t-1}}`{=tex} - 1 \]

**Daily percentage change**

\[ 100 `\times `{=tex}R_t \]

**Period price return**

\[ R\_{`\text{period}`{=tex}} =
`\frac{P_{\text{end}}}{P_{\text{start}}}`{=tex} - 1 \]

Calculate returns separately for each symbol and series after sorting by
date. Use adjusted prices if available for a corporate-action-aware
total-return calculation. If using unadjusted closes, label the metric
as a price return and explain that splits, dividends, and other
corporate actions can affect it.

## Volatility

A basic historical volatility estimate is the standard deviation of
daily returns:

\[ `\sigma`{=tex}\_{`\text{daily}`{=tex}} =
`\operatorname{StdDev}`{=tex}(R_t) \]

A common annualisation convention is:

\[ `\sigma`{=tex}*{`\text{annual}`{=tex}} =
`\sigma`{=tex}*{`\text{daily}`{=tex}}`\sqrt{252}`{=tex} \]

State this convention in the dashboard. The actual number of observed
trading sessions can vary.

## Trading activity and liquidity proxies

Potential measures:

-   Total traded volume.
-   Average and median daily volume.
-   Total and average reported turnover.
-   Number of trading sessions.
-   Number of zero-volume days, if present.

Volume and turnover are activity/liquidity proxies, not a complete
liquidity measure. Bid--ask spreads and order-book depth are not in the
current daily dataset.

## Company-level measures

-   Latest available close.
-   Period price return.
-   Average daily return.
-   Historical volatility.
-   Total volume and average turnover.
-   Highest and lowest observed close.
-   Number of available trading sessions.

Nominal share prices should not be used as a direct comparison of
company size or investment performance.

## Quarterly financial measures

-   Revenue by quarter.
-   Net profit by quarter.
-   EBITDA where available.
-   Revenue YoY growth where supplied or safely derived.
-   Net profit YoY growth where supplied or safely derived.
-   Consolidated versus standalone results.

Never combine standalone and consolidated results as though they were
equivalent. Make the reporting basis explicit.

## Correlation

Possible analyses:

-   Correlation between daily returns of selected stocks.
-   Correlation between monthly returns.
-   Relationship between quarterly financial growth and later stock
    returns, only if reporting dates and information availability are
    aligned correctly.

Use Pearson correlation for linear association and Spearman for rank
association. Align dates, state the missing-data policy, show the
overlapping sample size, and do not claim causation.

------------------------------------------------------------------------

# 7. Interactive dashboard --- detailed design

The dashboard is the user-facing analytics layer. It should read curated
datasets rather than repeatedly running the full ETL pipeline.

**Framework decision:** Not finalised. Streamlit is a practical Python
option. Power BI is another option for a more traditional
business-intelligence presentation. Keep the processed data independent
of the dashboard framework.

## Global layout

### Header

-   Project title: **NSE Big Data Analytics Platform**
-   Short description of the historical dataset.
-   Data coverage period.
-   Last successful pipeline run date.
-   Source-data note.

### Global filters

-   Date range.
-   NSE symbol/company.
-   Series: EQ, BE, BZ.
-   Sector, only if a reliable sector mapping exists.
-   Fiscal year and quarter.
-   Reporting basis: consolidated / standalone.

Filters should only affect relevant pages. For example, financial
reporting basis should not alter a price-only chart.

### Navigation pages

1.  Market Overview.
2.  Stock Explorer.
3.  Market Trends.
4.  Company Fundamentals.
5.  Correlation & Risk.
6.  Data Quality & Pipeline.

## Page 1 --- Market Overview

**Purpose:** Summarise the market activity in the selected period.

### KPI cards

-   Distinct symbols.
-   Number of trading dates.
-   Total traded volume.
-   Total reported turnover.
-   Average daily market volume.
-   Number of price records.

Display units and metric definitions. Avoid showing a metric until its
source units are verified.

### Charts

1.  **Market activity over time**
    -   X-axis: date or month.
    -   Y-axis: total volume.
    -   Show turnover in a separate chart because it has a different
        unit and scale.
2.  **Yearly market activity**
    -   X-axis: year.
    -   Y-axis: volume or turnover.
    -   Metric selector.
3.  **Series distribution**
    -   EQ / BE / BZ record counts.
    -   Explain that series are security classifications, not sectors.
4.  **Most actively traded symbols**
    -   Rank by total volume or turnover.
    -   Allow the user to switch the ranking metric.

### Interactions

-   Selecting a year filters other charts.
-   Selecting a symbol opens or filters Stock Explorer.
-   Tooltips show date, volume, turnover, and record count.

## Page 2 --- Stock Explorer

**Purpose:** Examine one stock's historical behaviour.

### Controls

-   Symbol search.
-   Date range.
-   Series.
-   Price field: close, open, high, low, last.
-   Price or percentage-return view.

### Charts

1.  Historical closing-price line chart.
2.  Daily return chart.
3.  Trading-volume bar chart.
4.  Rolling volatility chart, when implemented.
5.  Monthly/yearly return comparison.

### Summary metrics

-   First and last available close.
-   Period price return.
-   Highest and lowest close.
-   Average daily volume.
-   Total volume.
-   Annualised historical volatility.
-   Number of trading sessions.

### Correctness requirements

-   Sort by date before calculating returns.
-   Calculate returns separately for each symbol and series.
-   Do not calculate a return across an unrelated security row.
-   State whether prices are adjusted or unadjusted.

## Page 3 --- Market Trends

**Purpose:** Show how market activity and stock performance change over
time.

### Analyses and charts

-   Monthly market-volume line chart.
-   Year-over-year volume bar chart.
-   Turnover trend.
-   Daily return distribution histogram.
-   Best/worst observed price-return table for a selected period.
-   Volatility ranking.
-   Monthly seasonality view, if data supports it.

Use wording such as "highest observed price return in the selected
period", not "best investment".

## Page 4 --- Company Fundamentals

**Purpose:** Connect company reference information to quarterly
financial results.

### Company profile

-   Company name.
-   NSE symbol.
-   ISIN, where available.
-   Listing date, where available.
-   Current series / active status, where available.
-   Sector, only where the source supports it.

### Financial charts

-   Quarterly revenue.
-   Quarterly net profit.
-   EBITDA, where available.
-   Revenue YoY growth.
-   Net-profit YoY growth.
-   Consolidated versus standalone comparison.

### Controls

-   Company.
-   Fiscal year.
-   Quarter.
-   Reporting basis.
-   Financial metric.

### Coverage indicators

For each company show:

-   Number of quarters available.
-   First and last quarter.
-   Missing values in key financial fields.
-   Available reporting basis.

### Join warning

Company names and exchange codes may not match NSE symbols exactly.
Prefer ISIN or a reviewed mapping. Unmatched records should appear in a
data-quality report rather than being silently discarded.

## Page 5 --- Correlation & Risk

**Purpose:** Compare return behaviour and historical risk across
selected stocks.

### Controls

-   Select two or more symbols.
-   Date range.
-   Daily or monthly return frequency.
-   Pearson or Spearman method.

### Charts

-   Correlation heatmap.
-   Pairwise return scatter plot.
-   Cumulative price-return comparison.
-   Volatility comparison.
-   Rolling correlation as an optional extension.

### Methodology

-   Calculate each stock's returns independently.
-   Align observations by trading date.
-   Document missing-date handling.
-   Require a minimum number of overlapping observations.
-   Show sample size with each correlation.
-   Do not infer causation or guaranteed hedging from correlation.

## Page 6 --- Data Quality & Pipeline

**Purpose:** Make the engineering work visible and demonstrate
reproducibility.

### Pipeline status

-   Run timestamp.
-   Input file count.
-   Input row count.
-   Output row count.
-   Rows rejected by each validation rule.
-   Processing duration, once measured.
-   Output locations.
-   Pipeline success/failure status.

### Data-quality charts and tables

-   Null counts by important column.
-   Duplicate key count.
-   Invalid OHLC count.
-   Invalid volume/turnover count.
-   Records by year.
-   Records by series.
-   Company-master match rate.
-   Financial-data coverage by company and quarter.

### Spark/Hadoop information

Once measured, show:

-   Spark version.
-   Execution mode: local or cluster.
-   Storage type: local filesystem or HDFS.
-   Number of partitions.
-   File count and output size.
-   Job duration and stage information, where practical.

Do not claim distributed execution or performance improvement unless it
was actually measured.

------------------------------------------------------------------------

# 8. Curated data model and output layout

Suggested logical output structure:

``` text
dataset/
└── processed/
    ├── company_master/
    │   └── company_master.parquet
    ├── prices_clean/
    │   └── year=YYYY/
    ├── stock_summary/
    ├── yearly_summary/
    ├── monthly_summary/
    ├── daily_market_summary/
    ├── financial_results_clean/
    ├── company_financial_mapping/
    ├── stock_returns/
    │   └── year=YYYY/
    └── correlation/
```

These are proposed outputs; they do not all exist yet.

## Suggested tables

### `prices_clean`

Grain: one source price observation. Candidate key:
`(date, symbol, series)`, subject to duplicate validation.

### `stock_summary`

Grain: one row per symbol/series over a defined period.

Possible columns:

-   symbol, series
-   first_date, last_date
-   trading_sessions
-   average_close, minimum_close, maximum_close
-   total_volume, average_volume
-   total_turnover

### `yearly_summary`

Grain: one row per year, optionally split by series.

Possible columns:

-   year, series
-   record_count, distinct_symbols
-   total_volume, total_turnover
-   average_close

### `monthly_summary`

Grain: one row per year/month, optionally split by series.

### `daily_market_summary`

Grain: one row per trading date, optionally split by series.

### `financial_results_clean`

Grain: one company/quarter/reporting-basis observation after validation.

### `company_financial_mapping`

A reviewed mapping between a financial company identifier and an NSE
security identifier. If fuzzy matching is used, store the match method
and review status.

------------------------------------------------------------------------

# 9. Spark SQL learning plan

Once the DataFrame pipeline is stable, create temporary views and query
them using Spark SQL.

Example:

``` python
df_clean.createOrReplaceTempView("nse_prices")

spark.sql("""
    SELECT
        year,
        series,
        COUNT(*) AS record_count,
        COUNT(DISTINCT symbol) AS distinct_symbols,
        SUM(volume) AS total_volume
    FROM nse_prices
    GROUP BY year, series
    ORDER BY year, series
""").show()
```

Concepts to learn and demonstrate:

-   DataFrame creation and schema inspection.
-   `select`, `filter`, and `withColumn`.
-   Type conversion and date functions.
-   Null handling.
-   `groupBy` and aggregations.
-   Window functions for lagged prices and returns.
-   Joins and join validation.
-   Spark SQL.
-   Caching and persistence.
-   Partitioning and repartitioning.
-   Parquet read/write.
-   Execution plans using `explain()`.
-   Shuffle and data-skew awareness.
-   Adaptive Query Execution.
-   Basic performance measurement.

Understand why each operation is used; do not merely copy code.

------------------------------------------------------------------------

# 10. Storage and performance design

## Parquet

Parquet is a columnar format suited to analytical workloads. Queries can
read selected columns without loading every field. Use it for cleaned
and curated outputs.

## Partitioning

The cleaned price data is intended to be partitioned by year:

``` python
df_clean.write \
    .mode("overwrite") \
    .partitionBy("year") \
    .parquet(output_path)
```

Year partitioning can help when queries filter by year. Avoid
partitioning by high-cardinality fields such as symbol without a clear
reason; it can create excessive directories and small files.

## Caching

Caching `df_clean` can help when multiple actions reuse it. It consumes
memory, so release it when no longer needed:

``` python
df_clean.unpersist()
```

Do not cache every intermediate DataFrame automatically.

## Performance evidence to collect

Record actual:

-   Input data size.
-   Number of input files and records.
-   Runtime for each pipeline stage.
-   Output size.
-   Number of output partitions.
-   Hardware and Spark configuration.
-   Whether execution was local or distributed.

Only report measured results. Comparisons must use the same workload and
documented test conditions.

------------------------------------------------------------------------

# 11. Proposed project structure

``` text
BDA/
├── dataset/
│   ├── raw/
│   │   ├── nse/
│   │   └── company_master/
│   ├── interim/
│   └── processed/
├── code/
│   ├── ingestion/
│   ├── processing/
│   │   └── nse_spark_analysis.py
│   ├── analytics/
│   └── dashboard/
├── notebooks/
├── reports/
├── docs/
│   └── PROJECT_BLUEPRINT.md
├── tests/
├── requirements.txt
└── README.md
```

This is a proposed target structure. Not all folders or files
necessarily exist yet.

------------------------------------------------------------------------

# 12. Implementation roadmap

## Phase 1 --- Stabilise the environment

-   [x] Install Java.
-   [x] Install PySpark.
-   [x] Create a local Spark session.
-   [x] Run a simple DataFrame test.
-   [x] Discover all 17 yearly Parquet files.
-   [x] Read the complete NSE dataset.
-   [x] Apply initial cleaning; 7,342,169 rows remain.
-   [ ] Decide whether to repair native Windows setup or move to WSL2.
-   [ ] Get reliable Parquet output writing working.
-   [ ] Make the pipeline repeatable.

## Phase 2 --- Complete Spark ETL

-   [ ] Validate schema and data types.
-   [ ] Parse dates correctly.
-   [ ] Check duplicates.
-   [ ] Add OHLC consistency checks.
-   [ ] Validate volume and turnover.
-   [ ] Produce a rejection and quality report.
-   [ ] Write cleaned partitioned Parquet.
-   [ ] Create stock, yearly, monthly, and daily summaries.
-   [ ] Add Spark SQL queries.
-   [ ] Inspect execution plans and record timings.

## Phase 3 --- Security reference and financial integration

-   [ ] Validate the official NSE equity master.
-   [ ] Investigate duplicate ISINs.
-   [ ] Compare the official list with the secondary master.
-   [ ] Preserve historical symbols where possible.
-   [ ] Standardise quarterly financial data.
-   [ ] Separate consolidated and standalone results.
-   [ ] Build a reviewed company-to-symbol mapping.
-   [ ] Quantify mapping coverage and unmatched records.

## Phase 4 --- Analytics

-   [ ] Calculate daily returns.
-   [ ] Calculate cumulative price returns.
-   [ ] Calculate historical volatility.
-   [ ] Calculate volume and turnover summaries.
-   [ ] Build quarterly financial trend datasets.
-   [ ] Build correlation datasets.
-   [ ] Manually validate calculations on a small sample.

## Phase 5 --- Dashboard

-   [ ] Choose dashboard framework.
-   [ ] Create navigation, layout, and filters.
-   [ ] Build Market Overview.
-   [ ] Build Stock Explorer.
-   [ ] Build Market Trends.
-   [ ] Build Company Fundamentals.
-   [ ] Build Correlation & Risk.
-   [ ] Build Data Quality & Pipeline.
-   [ ] Test filters and missing-data states.
-   [ ] Ensure the dashboard reads curated outputs.

## Phase 6 --- Hadoop and integration

-   [ ] Learn HDFS architecture and commands.
-   [ ] Set up a small Hadoop environment.
-   [ ] Upload sample data to HDFS.
-   [ ] Verify blocks and replication.
-   [ ] Read HDFS data with Spark.
-   [ ] Write Spark outputs to HDFS.
-   [ ] Learn YARN components and execution flow.
-   [ ] Run Spark through YARN if the environment supports it.
-   [ ] Document local versus HDFS execution.

## Phase 7 --- Final report and demonstration

-   [ ] Document sources and attribution.
-   [ ] Explain ETL and data-quality decisions.
-   [ ] Explain Spark transformations and architecture.
-   [ ] Explain Hadoop/HDFS integration.
-   [ ] Present dashboard pages and findings.
-   [ ] Include measured performance results.
-   [ ] State data limitations and future improvements.

------------------------------------------------------------------------

# 13. Risks and decisions

  -----------------------------------------------------------------------
  Issue                   Why it matters          Response
  ----------------------- ----------------------- -----------------------
  Windows Hadoop          Output writes currently Prefer WSL2;
  filesystem issue        fail                    alternatively repair
                                                  Windows setup

  Current NSE list is a   Does not represent all  Preserve historical
  snapshot                historical listings     symbols and investigate
                                                  mappings

  Duplicate ISIN handling May remove meaningful   Inspect duplicates
                          reference rows          before deduplication

  Incomplete financial    Uneven company coverage Show coverage and
  results                                         missingness

  Company-name matching   Names may differ        Prefer ISIN/reviewed
                          between sources         mappings

  Unadjusted close prices Corporate actions may   Label price returns;
                          distort returns         obtain adjusted prices
                                                  if needed

  Local Spark execution   Does not prove          Describe it accurately;
                          multi-node scaling      add HDFS phase

  Reprocessing raw data   Slow and inconsistent   Use curated Parquet
  in dashboard                                    outputs
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 14. Current handover / immediate next step

At the latest confirmed run:

-   17 NSE yearly Parquet files are available.
-   Spark 4.3.0 starts.
-   Spark reads the complete dataset.
-   Current cleaning retains 7,342,169 rows.
-   Stock aggregation moved past the earlier unresolved-column error.
-   Output writing fails because Windows Hadoop filesystem support is
    not configured (`HADOOP_HOME` / `hadoop.home.dir` and `winutils.exe`
    warnings).
-   The next decision is native Windows repair versus WSL2 Ubuntu. WSL2
    is recommended, but migration has not been confirmed.

**Immediate priority: get a reliable Spark write working.** Do not build
the dashboard on unverified output files. Once ETL outputs are stable,
create the curated analytics tables and then build the dashboard.

## Implementation update — 10 November 2026

The implementation now includes a repeatable Spark ETL in
`code/processing/nse_spark_analysis.py`, a six-page Streamlit dashboard in
`code/dashboard/app.py`, dependency pins in `requirements.txt`, and run
instructions in `README.md`. The ETL validates required columns, parses
dates, checks OHLC consistency and negative activity fields, detects
duplicate date/symbol/series keys, retains zero-volume rows, derives
unadjusted daily returns, and defines cleaned prices plus stock, yearly,
monthly, daily, and Spark SQL outputs. It writes an explicit JSON quality
report and uses overwrite mode for reproducibility.

The full ETL was run successfully on this Windows installation using
Spark 4.3.0 in `local[*]`. All 17 source files and 7,342,169 input rows
were processed in 206.06 seconds. The current quality checks reported
zero invalid keys, unsupported series, non-positive prices, negative
activity values, OHLC inconsistencies, or duplicate keys; all rows were
retained. The quality report and all curated tables are under
`dataset/processed/spark_output/`. Hadoop 3.5.0 Windows native utilities
are included under `.hadoop-native/`, and `run_project.ps1` configures
the required paths, temp directory, and native library environment.
Streamlit and Plotly have also been installed in the project virtual
environment, and the dashboard server was started on port 8501.

The fundamentals page reports the supplied quarterly sample by company
name and basis, with coverage context. No automatic join to daily prices
is made because the project has no reviewed mapping. HDFS/YARN setup,
cluster execution, reference-master duplicate review, mapping review,
measured performance, and final demonstration remain incomplete. Spark
is still documented as local mode only. Browser UI inspection could not
be completed because the browser access host was unavailable; the local
Streamlit endpoint returned HTTP 200.

------------------------------------------------------------------------

# 15. Expected final deliverable

The completed project should demonstrate:

-   Multi-year NSE data ingestion.
-   Data cleaning and validation with PySpark.
-   Spark transformations and aggregations.
-   Parquet storage and partitioning.
-   Spark SQL analytics.
-   Hadoop HDFS concepts and a working Spark--HDFS integration.
-   Financial and market analysis with clear methodology.
-   An interactive dashboard with six analytical/operational pages.
-   Transparent data-quality reporting.
-   Reproducible pipeline execution and measured performance.

The strongest project outcome is not merely loading millions of rows. It
is showing that the data was ingested, validated, transformed, stored,
analysed, and presented through a documented pipeline, with measured
performance and honest limitations.
