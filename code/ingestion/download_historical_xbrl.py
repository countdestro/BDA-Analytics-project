
import sys
import time
import hashlib
import requests
import pandas as pd

from pathlib import Path
from xml.etree import ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Make the code folder accessible when this file is run directly
PROJECT_CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_CODE_DIR))

from config import RAW_DIR, XBRL_DIR
from logger import get_logger


logger = get_logger(__name__)

INPUT_FILE = RAW_DIR / "historical_api_diagnostic.csv"
MANIFEST_FILE = RAW_DIR / "xbrl_download_manifest.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/xml,text/xml,*/*",
    "Referer": "https://www.nseindia.com/"
}


def create_session():

    session = requests.Session()

    retry_strategy = Retry(
        total=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(HEADERS)

    return session


def create_filename(row, url):

    symbol = row["symbol"]
    period = pd.to_datetime(row["period_date"]).strftime("%Y-%m-%d")

    basis = str(row["consolidated"]).replace(" ", "_")
    cumulative = str(row["cumulative"]).replace(" ", "_")

    # Short hash prevents filename collisions between different filings
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

    filename = (
        f"{symbol}_{period}_{basis}_{cumulative}_{url_hash}.xml"
    )

    return filename


def download_xbrl(session, row):

    url = str(row["xbrl_url"]).strip()

    if not url.startswith("https://"):
        return "INVALID_URL", None, None

    symbol = row["symbol"]

    company_folder = XBRL_DIR / symbol
    company_folder.mkdir(parents=True, exist_ok=True)

    filename = create_filename(row, url)
    output_file = company_folder / filename

    # Avoid downloading an existing file again
    if output_file.exists() and output_file.stat().st_size > 0:
        return "ALREADY_EXISTS", str(output_file), 200

    try:
        response = session.get(
            url,
            timeout=60
        )

        response.raise_for_status()

        # Check whether the response is valid XML
        ET.fromstring(response.content)

        with open(output_file, "wb") as file:
            file.write(response.content)

        return "SUCCESS", str(output_file), response.status_code

    except requests.RequestException as error:
        logger.error(
            "Download failed for %s: %s",
            symbol,
            error
        )
        return "FAILED", None, getattr(
            getattr(error, "response", None),
            "status_code",
            None
        )

    except ET.ParseError as error:
        logger.error(
            "Invalid XML for %s: %s",
            symbol,
            error
        )
        return "INVALID_XML", None, response.status_code

    except OSError as error:
        logger.error(
            "File error for %s: %s",
            symbol,
            error
        )
        return "FILE_ERROR", None, None


def download_historical_xbrl():

    if not INPUT_FILE.exists():
        logger.error("Diagnostic CSV not found: %s", INPUT_FILE)
        return

    df = pd.read_csv(INPUT_FILE)

    required_columns = [
        "symbol",
        "period_date",
        "consolidated",
        "cumulative",
        "xbrl_url"
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        logger.error("Missing columns: %s", missing_columns)
        return

    df = df.dropna(subset=["xbrl_url"]).copy()

    # One XML document may appear more than once in the index
    df = df.drop_duplicates(subset=["xbrl_url"])

    logger.info("Unique XBRL documents to process: %d", len(df))

    session = create_session()

    manifest_records = []

    for index, row in df.iterrows():

        logger.info(
            "Processing %d of %d: %s",
            len(manifest_records) + 1,
            len(df),
            row["symbol"]
        )

        status, local_path, http_status = download_xbrl(
            session,
            row
        )

        manifest_records.append({
            "symbol": row["symbol"],
            "period_date": row["period_date"],
            "consolidated": row["consolidated"],
            "cumulative": row["cumulative"],
            "xbrl_url": row["xbrl_url"],
            "download_status": status,
            "http_status": http_status,
            "local_path": local_path
        })

        # Save progress periodically so results aren't lost
        if len(manifest_records) % 25 == 0:
            pd.DataFrame(manifest_records).to_csv(
                MANIFEST_FILE,
                index=False
            )

        time.sleep(0.3)

    manifest = pd.DataFrame(manifest_records)

    manifest.to_csv(
        MANIFEST_FILE,
        index=False
    )

    logger.info("XBRL DOWNLOAD COMPLETED")
    logger.info("Total documents: %d", len(manifest))

    logger.info(
        "Download summary:\n%s",
        manifest["download_status"].value_counts().to_string()
    )

    logger.info("Manifest saved: %s", MANIFEST_FILE)


if __name__ == "__main__":
    download_historical_xbrl()
