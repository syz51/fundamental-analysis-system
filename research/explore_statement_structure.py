"""Explore Statement structure for time series data"""

import pandas as pd
from edgar import Company, set_identity

set_identity("YourName your.email@example.com")

# Test with Apple
company = Company("AAPL")
filing = company.get_filings(form="10-K").latest(1)
obj = filing.obj()

print(f"Filing: {filing.form} filed {filing.filing_date}")
print("=" * 80)

# Get income statement (Statement object)
income_stmt = obj.income_statement
print(f"\nIncome Statement type: {type(income_stmt)}")
print(f"Income Statement class: {income_stmt.__class__.__name__}")

# Check if it's a DataFrame or has to_dataframe()
if isinstance(income_stmt, pd.DataFrame):
    print("✅ Statement IS a DataFrame")
    df = income_stmt
elif hasattr(income_stmt, "to_dataframe"):
    print("✅ Statement has to_dataframe() method")
    df = income_stmt.to_dataframe()
elif hasattr(income_stmt, "data"):
    print("✅ Statement has data attribute")
    df = income_stmt.data
    if isinstance(df, pd.DataFrame):
        print("   data is a DataFrame")
else:
    print("❌ Statement is not a DataFrame and has no to_dataframe()")

    # List all attributes
    import inspect

    members = inspect.getmembers(income_stmt)
    print("\nStatement attributes:")
    for name, value in members:
        if not name.startswith("_"):
            print(f"  {name}: {type(value).__name__}")

# If we have a DataFrame, explore it
try:
    if isinstance(df, pd.DataFrame):
        print(f"\n{'=' * 80}")
        print("DataFrame Structure:")
        print("=" * 80)
        print(f"Shape: {df.shape}")
        print(f"\nColumns: {list(df.columns)}")
        print("\nFirst few rows:")
        print(df.head())

        # Try to find revenue row
        print(f"\n{'=' * 80}")
        print("Finding Revenue:")
        print("=" * 80)

        # Check if there's a label or concept column
        if "label" in df.columns:
            revenue_rows = df[df["label"].str.contains("revenue", case=False, na=False)]
            print(f"Rows with 'revenue' in label: {len(revenue_rows)}")
            if not revenue_rows.empty:
                print("\nRevenue rows:")
                print(revenue_rows[["label"] + [col for col in df.columns if col != "label"]].head())

except Exception as e:
    print(f"Error exploring DataFrame: {e}")
    import traceback

    traceback.print_exc()

# Also test the Financials.income_statement() method
print(f"\n{'=' * 80}")
print("Testing Financials.income_statement() method:")
print("=" * 80)

try:
    fin_income_stmt = obj.financials.income_statement()
    print(f"Type: {type(fin_income_stmt)}")

    if isinstance(fin_income_stmt, pd.DataFrame):
        print(f"Shape: {fin_income_stmt.shape}")
        print(f"Columns: {list(fin_income_stmt.columns)}")
except Exception as e:
    print(f"Error: {e}")
