
import sys
from pathlib import Path

import pandas as pd

# Add the code directory to Python's import path
CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import PROCESSED_DIR

INPUT_FILE = PROCESSED_DIR / "raw_financial_facts.csv"


def inspect_financial_facts():

    # Load extracted XBRL facts
    df = pd.read_csv(INPUT_FILE)

    important_concepts = [
        "RevenueFromOperations",
        "Income",
        "OtherIncome",
        "ProfitBeforeTax",
        "ProfitLossForPeriod",
        "ProfitLossForPeriodFromContinuingOperations",
        "SegmentRevenue"
    ]

    for concept in important_concepts:

        result = df[df["concept"] == concept]

        print("\n" + "=" * 70)
        print(f"CONCEPT: {concept}")
        print(f"OBSERVATIONS: {len(result)}")
        print("=" * 70)

        if concept == "RevenueFromOperations":

            # Focus on TCS to investigate multiple reported values
            tcs = result[result["symbol"] == "TCS"]

            print("\nTCS REVENUE OBSERVATIONS")
            print("-" * 70)

            columns = [
                "symbol",
                "value",
                "context_id",
                "start_date",
                "end_date",
                "instant_date",
                "unit",
                "dimensions"
            ]

            print(
                tcs[columns]
                .head(12)
                .to_string(index=False)
            )

        else:

            columns = [
                "symbol",
                "value",
                "numeric_value",
                "unit",
                "start_date",
                "end_date",
                "instant_date",
                "dimensions"
            ]

            print(
                result[columns]
                .head(5)
                .to_string(index=False)
            )


if __name__ == "__main__":
    inspect_financial_facts()
