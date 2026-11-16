
from pathlib import Path
import pandas as pd
import logging

# --------------------------------------------------
# 1. PROJECT PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

FACTS_FILE = (
    BASE_DIR
    / "dataset"
    / "processed"
    / "raw_financial_facts_v3.csv"
)

OUTPUT_DIR = BASE_DIR / "dataset" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 100_000

# --------------------------------------------------
# 2. LOGGING
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# --------------------------------------------------
# 3. PROFILE DATASET
# --------------------------------------------------

def profile_dataset():

    logger.info("Starting financial data profiling")

    if not FACTS_FILE.exists():
        raise FileNotFoundError(
            f"Financial facts file not found: {FACTS_FILE}"
        )

    total_rows = 0

    missing_counts = {}
    company_counts = {}
    concept_counts = {}
    period_counts = {}
    column_names = None

    # Read CSV in chunks
    for chunk_number, chunk in enumerate(
        pd.read_csv(
            FACTS_FILE,
            chunksize=CHUNK_SIZE,
            low_memory=False
        ),
        start=1
    ):

        total_rows += len(chunk)

        if column_names is None:
            column_names = chunk.columns.tolist()

        # Missing values
        missing = chunk.isna().sum()

        for column, count in missing.items():
            missing_counts[column] = (
                missing_counts.get(column, 0) + count
            )

        # Company distribution
        if "symbol" in chunk.columns:
            counts = chunk["symbol"].value_counts(dropna=False)

            for company, count in counts.items():
                company_counts[company] = (
                    company_counts.get(company, 0) + count
                )

        # Financial concept distribution
        if "concept" in chunk.columns:
            counts = chunk["concept"].value_counts(dropna=False)

            for concept, count in counts.items():
                concept_counts[concept] = (
                    concept_counts.get(concept, 0) + count
                )

        # Period distribution
        if "period_type" in chunk.columns:
            counts = chunk["period_type"].value_counts(dropna=False)

            for period, count in counts.items():
                period_counts[period] = (
                    period_counts.get(period, 0) + count
                )

        logger.info(
            "Processed chunk %s | Total rows: %s",
            chunk_number,
            total_rows
        )

    # --------------------------------------------------
    # 4. GENERATE REPORTS
    # --------------------------------------------------

    logger.info("Generating profiling reports")

    # Missing values report
    missing_df = pd.DataFrame({
        "column": list(missing_counts.keys()),
        "missing_count": list(missing_counts.values())
    })

    missing_df["missing_percentage"] = (
        missing_df["missing_count"] / total_rows
    ) * 100

    missing_df = missing_df.sort_values(
        "missing_percentage",
        ascending=False
    )

    missing_df.to_csv(
        OUTPUT_DIR / "missing_values_report.csv",
        index=False
    )

    # Company distribution report
    company_df = pd.DataFrame(
        company_counts.items(),
        columns=["symbol", "record_count"]
    )

    company_df = company_df.sort_values(
        "record_count",
        ascending=False
    )

    company_df.to_csv(
        OUTPUT_DIR / "company_distribution_report.csv",
        index=False
    )

    # Concept distribution report
    concept_df = pd.DataFrame(
        concept_counts.items(),
        columns=["concept", "record_count"]
    )

    concept_df = concept_df.sort_values(
        "record_count",
        ascending=False
    )

    concept_df.to_csv(
        OUTPUT_DIR / "concept_distribution_report.csv",
        index=False
    )

    # Period distribution report
    period_df = pd.DataFrame(
        period_counts.items(),
        columns=["period_type", "record_count"]
    )

    period_df.to_csv(
        OUTPUT_DIR / "period_distribution_report.csv",
        index=False
    )

    # Dataset summary
    summary_df = pd.DataFrame({
        "metric": [
            "total_records",
            "total_columns",
            "total_companies",
            "total_concepts",
            "chunk_size"
        ],
        "value": [
            total_rows,
            len(column_names),
            len(company_counts),
            len(concept_counts),
            CHUNK_SIZE
        ]
    })

    summary_df.to_csv(
        OUTPUT_DIR / "dataset_summary.csv",
        index=False
    )

    logger.info("Profiling completed successfully")
    logger.info("Total records: %s", total_rows)
    logger.info("Reports saved in: %s", OUTPUT_DIR)


# --------------------------------------------------
# 5. MAIN
# --------------------------------------------------

if __name__ == "__main__":
    profile_dataset()
