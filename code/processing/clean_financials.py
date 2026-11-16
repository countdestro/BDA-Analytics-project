import pandas as pd
from config import PROCESSED_DIR
from logger import get_logger

logger=get_logger(__name__)
INPUT_FILE = PROCESSED_DIR / "selected_financial_filings.csv"

OUTPUT_FILE = PROCESSED_DIR / "clean_financial_filings.csv"

def clean_financials():
    df=pd.read_csv(INPUT_FILE,encoding="utf-8-sig")
    initial_count = len(df)
# Remove duplicate filing records
    df = df.drop_duplicates(
        subset=[
            "COMPANY NAME",
            "PERIOD ENDED",
            "PERIOD",
            "CONSOLIDATED / NON-CONSOLIDATED"
        ]
    )

    # Standardise text fields
    text_columns = df.select_dtypes(
        include=["object"]
    ).columns

    for column in text_columns:
        df[column] = df[column].astype("string").str.strip()

    # Convert period-ended column to date
    df["PERIOD ENDED"] = pd.to_datetime(
        df["PERIOD ENDED"],
        errors="coerce",
        dayfirst=True
    )

    # Remove records without essential identifiers
    df = df.dropna(
        subset=[
            "COMPANY NAME",
            "PERIOD ENDED"
        ]
    )

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    logger.info("Original records: %d", initial_count)
    logger.info("Clean records: %d", len(df))
    logger.info("Saved cleaned filing data: %s", OUTPUT_FILE)

    return df
