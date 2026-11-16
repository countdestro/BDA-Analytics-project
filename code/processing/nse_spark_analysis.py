"""Reproducible Spark ETL for the historical NSE daily price dataset.

Run from any directory with the project's Python environment:
    python code/processing/nse_spark_analysis.py

On Windows, Hadoop's local filesystem may require a compatible winutils.exe.
Set HADOOP_HOME before running if Spark reports that it is missing.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("PYSPARK_DRIVER_PYTHON", sys.executable)

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "dataset" / "raw" / "nse"
OUTPUT_DIR = PROJECT_DIR / "dataset" / "processed" / "spark_output"


def main() -> None:
    files = sorted(DATA_DIR.rglob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No yearly parquet files found under {DATA_DIR}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    spark = (SparkSession.builder.appName("NSE-Big-Data-Analytics")
             .master("local[*]").config("spark.driver.memory", "6g")
             .config("spark.sql.shuffle.partitions", "12")
             .config("spark.sql.adaptive.enabled", "true")
             .config("spark.sql.legacy.timeParserPolicy", "CORRECTED")
             .getOrCreate())
    spark.sparkContext.setLogLevel("WARN")
    started = time.perf_counter()
    try:
        paths = [p.resolve().as_posix() for p in files]
        raw = spark.read.parquet(*paths)
        required = {"date", "symbol", "series", "open", "high", "low", "close", "volume"}
        missing = sorted(required - set(raw.columns))
        if missing:
            raise ValueError(f"Input schema is missing required columns: {missing}")

        # Normalize dates and numeric fields while preserving optional metadata.
        normalized = raw.withColumn("date", F.to_date("date"))
        for name in ("open", "high", "low", "close", "volume", "turnover", "trades", "prev_close", "last"):
            if name in normalized.columns:
                normalized = normalized.withColumn(name, F.col(name).cast("double"))
        normalized = (normalized
            .withColumn("symbol", F.upper(F.trim("symbol")))
            .withColumn("series", F.upper(F.trim("series")))
            .withColumn("year", F.year("date")))

        key = ["date", "symbol", "series"]
        bad_key = F.col("date").isNull() | F.col("symbol").isNull() | (F.col("symbol") == "") | F.col("series").isNull()
        invalid_series = ~F.col("series").isin("EQ", "BE", "BZ")
        bad_price = (F.col("open") <= 0) | (F.col("high") <= 0) | (F.col("low") <= 0) | (F.col("close") <= 0)
        bad_volume = F.col("volume") < 0
        bad_ohlc = ((F.col("high") < F.col("low")) |
                    (F.col("high") < F.greatest("open", "close")) |
                    (F.col("low") > F.least("open", "close")))
        bad_turnover = F.col("turnover").isNotNull() & (F.col("turnover") < 0) if "turnover" in normalized.columns else F.lit(False)
        bad_trades = F.col("trades").isNotNull() & (F.col("trades") < 0) if "trades" in normalized.columns else F.lit(False)
        duplicate_window = Window.partitionBy(*key)
        marked = (normalized.withColumn("_duplicate_count", F.count(F.lit(1)).over(duplicate_window))
                  .withColumn("_duplicate", F.col("_duplicate_count") > 1)
                  .withColumn("_bad_key", bad_key)
                  .withColumn("_bad_series", invalid_series)
                  .withColumn("_bad_price", bad_price)
                  .withColumn("_bad_volume", bad_volume)
                  .withColumn("_bad_ohlc", bad_ohlc)
                  .withColumn("_bad_turnover", bad_turnover)
                  .withColumn("_bad_trades", bad_trades))
        metrics = [F.count(F.lit(1)).alias("input_rows")]
        for label in ("bad_key", "bad_series", "bad_price", "bad_volume", "bad_ohlc", "bad_turnover", "bad_trades", "duplicate"):
            metrics.append(F.sum(F.col("_" + label).cast("long")).alias(label + "_rows"))
        qc = marked.agg(*metrics).first().asDict()
        valid = marked.filter(~(F.col("_bad_key") | F.col("_bad_series") | F.col("_bad_price") |
                                F.col("_bad_volume") | F.col("_bad_ohlc") | F.col("_bad_turnover") |
                                F.col("_bad_trades") | F.col("_duplicate")))
        # Keep zero volume: it is a quality indicator, not by itself an invalid price observation.
        clean = valid.drop("_duplicate_count", "_bad_key", "_bad_series", "_bad_price", "_bad_volume", "_bad_ohlc",
                           "_bad_turnover", "_bad_trades", "_duplicate")
        if "month" not in clean.columns:
            clean = clean.withColumn("month", F.month("date"))

        w = Window.partitionBy("symbol", "series").orderBy("date")
        prices = (clean.withColumn("previous_close", F.lag("close").over(w))
                  .withColumn("daily_return", F.col("close") / F.col("previous_close") - 1)
                  .withColumn("daily_return_pct", 100 * F.col("daily_return"))
                  .withColumn("month_start", F.trunc("date", "month")))

        stock = prices.groupBy("symbol", "series").agg(
            F.min("date").alias("first_date"), F.max("date").alias("last_date"),
            F.count("*").alias("trading_days"), F.max_by("close", "date").alias("latest_close"),
            F.min("close").alias("minimum_close"), F.max("close").alias("maximum_close"),
            F.avg("close").alias("average_close"), F.sum("volume").alias("total_volume"),
            F.avg("volume").alias("average_volume"), F.avg("turnover").alias("average_turnover") if "turnover" in prices.columns else F.lit(None).alias("average_turnover"),
            F.stddev_samp("daily_return").alias("daily_volatility"),
            (F.stddev_samp("daily_return") * F.sqrt(F.lit(252))).alias("annualized_volatility"),
            (F.max_by("close", "date") / F.min_by("close", "date") - 1).alias("period_price_return"))
        yearly = prices.groupBy("year", "series").agg(
            F.count("*").alias("total_records"), F.countDistinct("symbol").alias("active_symbols"),
            F.avg("close").alias("average_close"), F.sum("volume").alias("total_volume"),
            F.sum("turnover").alias("total_turnover") if "turnover" in prices.columns else F.lit(None).alias("total_turnover"))
        monthly = prices.groupBy("month_start", "series").agg(
            F.count("*").alias("total_records"), F.countDistinct("symbol").alias("active_symbols"),
            F.avg("close").alias("average_close"), F.sum("volume").alias("total_volume"),
            F.sum("turnover").alias("total_turnover") if "turnover" in prices.columns else F.lit(None).alias("total_turnover"))
        daily = prices.groupBy("date", "series").agg(
            F.count("*").alias("listed_observations"), F.countDistinct("symbol").alias("active_symbols"),
            F.sum("volume").alias("total_volume"), F.sum("turnover").alias("total_turnover") if "turnover" in prices.columns else F.lit(None).alias("total_turnover"),
            F.avg("daily_return").alias("mean_stock_return"))

        # Outputs are written in explicit overwrite mode and can be rebuilt from the immutable raw files.
        for name, frame, partition in [
            ("prices_clean", prices, "year"), ("stock_summary", stock, None),
            ("yearly_summary", yearly, "year"), ("monthly_summary", monthly, None),
            ("daily_market_summary", daily, None)]:
            writer = frame.write.mode("overwrite")
            if partition:
                writer = writer.partitionBy(partition)
            writer.parquet((OUTPUT_DIR / name).as_posix())

        clean_count = prices.count()
        qc.update({"clean_rows": clean_count,
                   "zero_volume_rows": prices.filter(F.col("volume") == 0).count(),
                   "distinct_symbols": prices.select("symbol").distinct().count(),
                   "source_files": len(files), "spark_version": spark.version,
                   "execution_mode": "local[*]", "elapsed_seconds": round(time.perf_counter() - started, 2),
                   "methodology": "Daily returns use unadjusted close; annualized volatility uses sqrt(252). Duplicate date-symbol-series keys are excluded."})
        (OUTPUT_DIR / "quality_report.json").write_text(json.dumps(qc, indent=2, default=str), encoding="utf-8")
        prices.createOrReplaceTempView("nse_prices")
        spark.sql("SELECT year, series, count(*) AS rows, count(distinct symbol) AS symbols FROM nse_prices GROUP BY year, series ORDER BY year, series").write.mode("overwrite").option("header", True).csv((OUTPUT_DIR / "spark_sql_year_series").as_posix())
        print(json.dumps(qc, indent=2, default=str))
        print(f"Curated Spark outputs: {OUTPUT_DIR}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()
