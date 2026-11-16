from pathlib import Path
BASE_DIR=Path(__file__).resolve().parent.parent
DATASET_DIR=BASE_DIR/"dataset"
RAW_DIR=DATASET_DIR/"raw"
PROCESSED_DIR=DATASET_DIR/"processed"
OUTPUT_DIR=DATASET_DIR/"output"
XBRL_DIR = RAW_DIR / "xbrl"

LOG_DIR = BASE_DIR / "logs"
START_DATE="2005-01-01"
END_DATE="2026-04-01"
COMPANIES = {
    "HDFCBANK": "HDFC Bank Limited",
    "ICICIBANK": "ICICI Bank Limited",
    "SBIN": "State Bank of India",
    "TCS": "Tata Consultancy Services Limited",
    "INFY": "Infosys Limited",
    "WIPRO": "Wipro Limited",
    "RELIANCE": "Reliance Industries Limited",
    "NTPC": "NTPC Limited",
    "BDL": "Bharat Dynamics Limited",
    "BEL": "Bharat Electronics Limited",
    "HAL": "Hindustan Aeronautics Limited"
}
YAHOO_SYMBOLS = {
        symbol:f"{symbol}.NS"
        for symbol in COMPANIES
}
NSE_BASE_URL = "https://www.nseindia.com"

NSE_FINANCIAL_API = (
    f"{NSE_BASE_URL}/api/corporates-financial-results"
    "?index=equities&fo_sec=true&period=Quarterly&csv=true"
)

# Create directories if missing
for directory in [
    RAW_DIR,
    PROCESSED_DIR,
    OUTPUT_DIR,
    XBRL_DIR,
    LOG_DIR
]:
    directory.mkdir(parents=True, exist_ok=True)