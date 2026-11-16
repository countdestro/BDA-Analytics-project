
import sys
from pathlib import Path
import pandas as pd

CODE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_DIR))

from config import PROCESSED_DIR

INPUT_FILE = PROCESSED_DIR / "raw_financial_facts.csv"


def inspect_extracted_data():

    df = pd.read_csv(INPUT_FILE)

    print("\nDATASET SHAPE")
    print(df.shape)

    print("\nCOLUMNS")
    print(df.columns.tolist())

    print("\nDATA TYPES")
    print(df.dtypes)

    print("\nTOP 50 MOST FREQUENT CONCEPTS")
    print(
        df["concept"]
        .value_counts()
        .head(50)
        .to_string()
    )

    print("\nMISSING VALUES")
    print(df.isnull().sum())

    print("\nSAMPLE FINANCIAL FACTS")
    print(
        df[
            ["symbol", "concept", "value", "unit",
             "start_date", "end_date", "instant_date"]
        ].head(20).to_string(index=False)
    )


if __name__ == "__main__":
    inspect_extracted_data()
