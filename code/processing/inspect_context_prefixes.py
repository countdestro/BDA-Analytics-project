import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

FILE = BASE_DIR / "dataset" / "processed" / "raw_financial_facts_v2.csv"

df = pd.read_csv(FILE)

concepts = [
    "RevenueFromOperations",
    "ProfitBeforeTax",
    "ProfitLossForPeriod"
]

result = df[
    df["concept"].isin(concepts)
    & df["context_ref"].isin(["OneD", "FourD"])
]

summary = (
    result.groupby(["symbol", "reporting_date", "concept", "context_ref"])
    .agg(
        value=("numeric_value", "first"),
        start_date=("start_date", "first"),
        end_date=("end_date", "first"),
        source_file=("source_file", "first")
    )
    .reset_index()
)

print(summary.to_string(index=False))