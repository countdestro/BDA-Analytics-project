import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FILE = BASE_DIR / "dataset" / "processed" / "raw_financial_facts_v2.csv"

df = pd.read_csv(FILE)

result = df[
    (df["symbol"] == "TCS")
    & (df["reporting_date"] == "2024-12-31")
    & (df["concept"].str.contains("Revenue|Income|Profit", case=False, na=False))
]

columns = [
    "source_file",
    "concept",
    "value",
    "context_ref",
    "start_date",
    "end_date",
    "instant_date",
    "unit",
    "dimensions"
]

print(result[columns].to_string(index=False))