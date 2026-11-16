from logger import get_logger

from ingestion.download_financials import download_financial_data
from ingestion.download_stock_data import download_stock_data

from processing.inspect_financials import inspect_financials
from extraction.extract_xbrl import extract_xbrl_files
from processing.clean_financials import clean_financials

from analytics.financial_analysis import analyse_stock_performance

logger = get_logger(__name__)


def run_pipeline():

    logger.info("Starting BDA project pipeline")

    # Stage 1: Data ingestion
    download_financial_data()
    download_stock_data()

    # Stage 2: Filing inspection
    inspect_financials()

    # Stage 3: XBRL document download
    extract_xbrl_files()

    # Stage 4: Filing metadata cleaning
    clean_financials()

    # Stage 5: Stock performance analysis
    analyse_stock_performance()

    logger.info("BDA project pipeline completed successfully")


if __name__ == "__main__":
    run_pipeline()