import pandas as pd

file_path = "dataset/processed/raw_financial_facts_v3.csv"

chunk_size = 100_000

total_rows = 0

for chunk in pd.read_csv(
    file_path,
    chunksize=chunk_size,
    low_memory=False
):
    total_rows += len(chunk)

print("Total records:", total_rows)