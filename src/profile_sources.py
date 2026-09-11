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
    with open(path, encoding='utf-8') as f:
        data = json.load(f)

    size_kb = path.stat().st_size / 1024
    print(f"\n=== {path.name} ===")
    print(f"file size: {size_kb:.1f} KB")
    print(f"root structure: {type(data).__name__}")
    print(f"record count: {len(data)}")

    all_keys = set()
    for record in data:
        all_keys.update(record.keys())
    print(f"\ntop-level keys: {sorted(all_keys)}")

    print("\nfield analysis:")
    sample = data[0]
    for key in sorted(all_keys):
        value = sample.get(key)
        if isinstance(value, dict):
            kind = f"nested object (keys: {sorted(value.keys())})"
        elif isinstance(value, list):
            kind = "nested array"
        elif isinstance(value, bool):
            kind = "boolean"
        elif isinstance(value, (int, float)):
            kind = "numeric"
        elif isinstance(value, str) and ("time" in key.lower() or "date" in key.lower()):
            kind = "timestamp (as text)"
        else:
            kind = "string"
        print(f"  {key:<18} {kind}")

    print("\nmissing or null values per key:")
    for key in sorted(all_keys):
        missing = sum(1 for r in data if key not in r or r[key] is None)
        print(f"  {key:<18} {missing}")

    nested_keys = [k for k in all_keys if isinstance(sample.get(k), dict)]
    print(f"\nnested fields: {nested_keys}")


def profile_parquet(path):
    df = pd.read_parquet(path)
    size_kb = path.stat().st_size / 1024

    print(f"\n=== {path.name} ===")
    print(f"file size: {size_kb:.1f} KB")
    print(f"rows: {df.shape[0]}  columns: {df.shape[1]}")

    print("\ndtypes as read from parquet:")
    print(df.dtypes)

    print("\nmissing values per column:")
    print(df.isna().sum())

    print("\nfirst three records:")
    print(df.head(3))

    # Format comparison: same 200 products stored three ways
    csv_path = path.parent / 'products_optional_compare.csv'
    json_path = path.parent / 'products_optional_compare.json'

    if csv_path.exists() and json_path.exists():
        df_csv = pd.read_csv(csv_path)
        df_json = pd.read_json(json_path)

        print("\n--- format comparison (same 200 products) ---")
        print(f"parquet: {size_kb:6.1f} KB")
        print(f"csv:     {csv_path.stat().st_size / 1024:6.1f} KB")
        print(f"json:    {json_path.stat().st_size / 1024:6.1f} KB")

        print("\ndtypes by format:")
        comparison = pd.DataFrame({
            'parquet': df.dtypes.astype(str),
            'csv': df_csv.dtypes.astype(str),
            'json': df_json.dtypes.astype(str),
        })
        print(comparison)


if __name__ == '__main__':
    profile_csv(DATA_DIR / 'customers.csv')
    profile_json(DATA_DIR / 'orders.json')
    profile_parquet(DATA_DIR / 'products.parquet')
    