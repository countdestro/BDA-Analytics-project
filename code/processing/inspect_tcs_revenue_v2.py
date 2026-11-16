
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE_DIR
    / "dataset"
    / "processed"
    / "raw_financial_facts_v2.csv"
)

df = pd.read_csv(INPUT_FILE)

result = df[
    (df["symbol"] == "TCS")
    & (df["concept"] == "RevenueFromOperations")
    & (df["reporting_date"] == "2024-12-31")
]

columns = [
    "source_file",
    "reporting_basis",
    "filing_type",
    "concept_qname",
    "value",
    "context_ref",
    "start_date",
    "end_date",
    "unit_ref",
    "decimals",
    "dimensions"
]

print("\nTCS REVENUE FACTS - DECEMBER 2024")
print("=" * 100)

if result.empty:
    print("No matching revenue facts found.")
else:
    print(result[columns].to_string(index=False))

print("\nTOTAL OBSERVATIONS:", len(result))
