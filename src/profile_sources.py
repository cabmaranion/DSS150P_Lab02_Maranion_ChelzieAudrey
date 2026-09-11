"""Week 2 starter: profile CSV, JSON, Parquet, API payload, and PostgreSQL table.
Complete the TODOs. Do not hard-code expected counts.
"""
from pathlib import Path
import json, csv
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'


def profile_csv(path):
    df = pd.read_csv(path)
    size_kb = path.stat().st_size / 1024

    print(f"\n=== {path.name} ===")
    print(f"file size: {size_kb:.1f} KB")
    print(f"rows: {df.shape[0]}  columns: {df.shape[1]}")

    print("\ncolumns and inferred logical types:")
    for col in df.columns:
        pandas_type = str(df[col].dtype)
        sample = df[col].dropna().iloc[0] if df[col].notna().any() else ""
        if "date" in col.lower():
            logical = "date"
        elif pandas_type.startswith("int") or pandas_type.startswith("float"):
            logical = "number"
        else:
            logical = "string"
        print(f"  {col:<18} pandas={pandas_type:<10} logical={logical}")

    print("\nmissing values per column:")
    print(df.isna().sum())

    print(f"\nexact duplicate rows: {df.duplicated().sum()}")

    total = len(df)
    distinct_ids = df['customer_id'].nunique()
    print(f"\ncustomer_id: {distinct_ids} distinct out of {total} rows")
    print(f"customer_id unique? {distinct_ids == total}")

    if distinct_ids < total:
        repeated = df['customer_id'].value_counts()
        repeated = repeated[repeated > 1]
        print("repeated customer_id values:")
        print(repeated)


def profile_json(path):
    # TODO: record count, keys, nested fields, date/time fields, numeric fields, nulls
    pass


def profile_parquet(path):
    # TODO: use pandas.read_parquet; report rows/columns/dtypes/nulls and file size
    pass


if __name__ == '__main__':
    profile_csv(DATA_DIR / 'customers.csv')
    profile_json(DATA_DIR / 'orders.json')
    profile_parquet(DATA_DIR / 'products.parquet')
    