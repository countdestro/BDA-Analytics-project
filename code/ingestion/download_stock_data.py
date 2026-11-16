import yfinance as yf
import pandas as pd

from config import (
    YAHOO_SYMBOLS,
    START_DATE,
    END_DATE,
    RAW_DIR
)

from logger import get_logger

logger = get_logger(__name__)


def download_stock_data():

    all_data = []

    for company, yahoo_symbol in YAHOO_SYMBOLS.items():

        try:
            logger.info("Downloading %s", company)

            data = yf.download(
                yahoo_symbol,
                start=START_DATE,
                end=END_DATE,
                interval="1d",
                auto_adjust=False,
                progress=False
            )

            if data.empty:
                logger.warning("No data found for %s", company)
                continue

            # Handle possible multi-level column names
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)

            data = data.reset_index()

            data["Company"] = company

            all_data.append(data)

        except Exception:
            logger.exception(
                "Stock download failed for %s",
                company
            )

    if not all_data:
        raise RuntimeError("No stock data was downloaded")

    combined = pd.concat(
        all_data,
        ignore_index=True
    )

    output_file = RAW_DIR / "nse_stock_data.csv"

    combined.to_csv(
        output_file,
        index=False
    )

    logger.info("Stock dataset saved: %s", output_file)

    return output_file


if __name__ == "__main__":
    download_stock_data()