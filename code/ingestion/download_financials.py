import requests
from config import NSE_BASE_URL, NSE_FINANCIAL_API, RAW_DIR
from logger import get_logger
logger = get_logger(__name__)

OUTPUT_FILE = RAW_DIR / "nse_financial_results.csv"
def download_financial_data():
    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/csv,application/json,*/*",
        "Referer": NSE_BASE_URL + "/",
        "Accept-Language": "en-US,en;q=0.9"
    })
    try:
        logger.info("Connecting to NSE")

        homepage = session.get(
            NSE_BASE_URL,
            timeout=20
        )

        homepage.raise_for_status()

        response = session.get(
            NSE_FINANCIAL_API,
            timeout=60
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "csv" not in content_type:
            raise ValueError(
                f"Unexpected response: {content_type}"
            )

        if not response.content:
            raise ValueError("Empty NSE response")

        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        OUTPUT_FILE.write_bytes(response.content)

        logger.info("Financial filing CSV saved: %s", OUTPUT_FILE)

        return OUTPUT_FILE

    except Exception:
        logger.exception("Financial data ingestion failed")
        raise

    finally:
        session.close()

if __name__ == "__main__":
    download_financial_data()