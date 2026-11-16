import pandas as pd

df = pd.read_csv(
    "dataset/raw/company_master/india_quarterly_results_sample.csv"
)

coverage = (
    df.groupby("company_name")
    .agg(
        quarters=("quarter_end", "nunique"),
        revenue_records=("revenue_inr", "count"),
        profit_records=("net_profit_inr", "count")
    )
    .sort_values("quarters", ascending=False)
)

print("COMPANIES WITH MOST QUARTERS:")
print(coverage.head(20).to_string())

print("\nQUARTER COVERAGE DISTRIBUTION:")
print(coverage["quarters"].value_counts().sort_index().to_string())

print("\nCOMPANIES WITH AT LEAST 20 QUARTERS:")
print((coverage["quarters"] >= 20).sum())