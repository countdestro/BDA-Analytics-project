import sys
import time
import requests
import pandas as pd

from datetime import datetime
from pathlib import Path

# Make the code folder accessible when this file is run directly
PROJECT_CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_CODE_DIR))

from config import RAW_DIR


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_URL = "https://www.nseindia.com"

API_URL = "https://www.nseindia.com/api/corporates-financial-results"

COMPANY_FILE = RAW_DIR / "company_universe.csv"
OUTPUT_FILE = RAW_DIR / "historical_api_diagnostic.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nseindia.com/"
}

START_DATE = datetime(2005, 1, 1)
END_DATE = datetime(2026, 4, 1)

REQUEST_DELAY_SECONDS = 1


# --------------------------------------------------
# LOAD COMPANY UNIVERSE
# --------------------------------------------------

def load_companies():

    if not COMPANY_FILE.exists():
        raise FileNotFoundError(
            f"Company universe file not found: {COMPANY_FILE}"
        )

    companies_df = pd.read_csv(COMPANY_FILE)

    required_columns = ["symbol", "company_name"]

    missing_columns = [
        column for column in required_columns
        if column not in companies_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns: {missing_columns}"
        )

    companies_df = companies_df.dropna(
        subset=["symbol", "company_name"]
    ).copy()

    companies_df["symbol"] = (
        companies_df["symbol"].astype(str).str.strip().str.upper()
    )

    companies_df["company_name"] = (
        companies_df["company_name"].astype(str).str.strip()
    )

    companies_df = companies_df.drop_duplicates(
        subset=["symbol"]
    )

    if companies_df.empty:
        raise ValueError("No valid companies found.")

    return companies_df


# --------------------------------------------------
# NSE SESSION
# --------------------------------------------------

def create_session():

    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        homepage = session.get(
            BASE_URL,
            timeout=20
        )

        print("NSE homepage status:", homepage.status_code)

    except requests.RequestException as error:
        print("NSE homepage warning:", error)

    return session


# --------------------------------------------------
# FETCH COMPANY RECORDS
# --------------------------------------------------

def fetch_company_records(session, symbol, company_name):

    params = {
        "index": "equities",
        "symbol": symbol,
        "period": "Quarterly"
    }

    try:
        response = session.get(
            API_URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()
        records = response.json()

    except (requests.RequestException, ValueError) as error:
        print(f"Request failed for {symbol}: {error}")
        return []

    if not isinstance(records, list):
        print(f"Unexpected API response for {symbol}.")
        return []

    print("Raw API records:", len(records))

    company_records = []

    for record in records:

        try:
            period_date = datetime.strptime(
                record["toDate"],
                "%d-%b-%Y"
            )

        except (ValueError, TypeError, KeyError):
            continue

        if not (START_DATE <= period_date < END_DATE):
            continue

        company_records.append({
            "symbol": symbol,
            "company": company_name,
            "period_date": period_date,
            "financial_year": record.get("financialYear"),
            "quarter": record.get("relatingTo"),
            "consolidated": record.get("consolidated"),
            "cumulative": record.get("cumulative"),
            "xbrl_url": record.get("xbrl"),
            "filing_date": record.get("filingDate")
        })

    return company_records


# --------------------------------------------------
# MAIN DISCOVERY PROCESS
# --------------------------------------------------

def download_historical_records():

    companies_df = load_companies()

    print("Companies loaded:", len(companies_df))

    session = create_session()
    all_records = []

    total_companies = len(companies_df)

    for company_number, company in enumerate(
        companies_df.itertuples(index=False),
        start=1
    ):

        symbol = company.symbol
        company_name = company.company_name

        print("\n" + "=" * 60)
        print(f"Company {company_number} of {total_companies}")
        print("Company:", company_name)
        print("Symbol:", symbol)
        print("=" * 60)

        company_records = fetch_company_records(
            session,
            symbol,
            company_name
        )

        all_records.extend(company_records)

        if company_records:

            df_company = pd.DataFrame(company_records)

            print(
                "Earliest period:",
                df_company["period_date"].min().date()
            )

            print(
                "Latest period:",
                df_company["period_date"].max().date()
            )

            print("Valid historical records:", len(df_company))

            print("\nReporting basis:")

            print(
                df_company["consolidated"]
                .value_counts(dropna=False)
            )

            print("\nRecords before 2021:")

            print(
                (df_company["period_date"].dt.year < 2021).sum()
            )

        else:
            print("No valid historical records found.")

        time.sleep(REQUEST_DELAY_SECONDS)

    if not all_records:
        print("\nNo historical records collected.")
        return

    df = pd.DataFrame(all_records)



    df["year"] = df["period_date"].dt.year

    # --------------------------------------------------
    # COMPANY-WISE COVERAGE
    
    # --------------------------------------------------

    print("\nCOMPANY-WISE HISTORICAL COVERAGE")

    coverage = df.groupby("symbol").agg(
        first_period=("period_date", "min"),
        latest_period=("period_date", "max"),
        total_records=("period_date", "count")
    )

    print(coverage)

    # --------------------------------------------------
    # REPORTING BASIS
    # --------------------------------------------------

    print("\nREPORTING BASIS SUMMARY")

    print(
        pd.crosstab(
            df["symbol"],
            df["consolidated"]
        )
    )

    # --------------------------------------------------
    # YEAR-WISE RECORD COUNTS
    # --------------------------------------------------

    print("\nRECORD COUNTS BY COMPANY AND YEAR")

    print(
        pd.crosstab(
            df["symbol"],
            df["year"]
        )
    )

    # --------------------------------------------------
    # PRE-2021 COVERAGE
    # --------------------------------------------------

    print("\nPRE-2021 HISTORICAL RECORDS")

    older_records = df[df["year"] < 2021]

    if not older_records.empty:

        older_summary = older_records.groupby("symbol").agg(
            first_period=("period_date", "min"),
            latest_period=("period_date", "max"),
            older_records=("period_date", "count")
        )

        print(older_summary)

    else:
        print("No records before 2021.")

    # --------------------------------------------------
    # XBRL AVAILABILITY
    # --------------------------------------------------

    print("\nXBRL LINK AVAILABILITY")

    df["has_xbrl"] = (
        df["xbrl_url"].notna()
        & df["xbrl_url"].astype(str).str.startswith("http")
    )

    print(
        df.groupby("symbol")["has_xbrl"]
        .agg(["sum", "count"])
    )

    # --------------------------------------------------
    # SAVE DIAGNOSTIC DATASET
    # --------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print("\nDIAGNOSTIC COMPLETED")

    print("Total records:", len(df))
    print("Companies covered:", df["symbol"].nunique())
    print("Saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    download_historical_records()