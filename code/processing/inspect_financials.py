
import pandas as pd

from config import RAW_DIR, PROCESSED_DIR, COMPANIES
from logger import get_logger

logger = get_logger(__name__)

INPUT_FILE = RAW_DIR / "nse_financial_results.csv"
OUTPUT_FILE = PROCESSED_DIR / "selected_financial_filings.csv"


def inspect_financials():

    # Read raw NSE filing data
    df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")

    # Clean column names
    df.columns = df.columns.str.strip()

    logger.info("Total NSE filing records: %d", len(df))

    # Select our 11 companies
    company_names = list(COMPANIES.values())

    company_column = df["COMPANY NAME"].astype(str).str.strip()

    selected = df[company_column.isin(company_names)].copy()

    # Keep consolidated financial statements
    selected = selected[
        selected["CONSOLIDATED / NON-CONSOLIDATED"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("consolidated")
    ].copy()

    # Keep valid XBRL URLs
    xbrl_column = "** XBRL"

    selected[xbrl_column] = selected[xbrl_column].astype(str).str.strip()

    selected = selected[
        selected[xbrl_column].str.startswith("https://", na=False)
    ].copy()

    # Save selected filings
    selected.to_csv(OUTPUT_FILE, index=False)

    logger.info("Selected filing records: %d", len(selected))
    logger.info("Saved selected filings: %s", OUTPUT_FILE)

    return selected


if __name__ == "__main__":
    inspect_financials()
