"""
Examine EdgarTools DataFrame structure in detail
"""

import logging

from edgar import Company, set_identity

logging.basicConfig(level=logging.WARNING)

set_identity("research@example.com")


def main():
    """Examine DataFrame structure."""
    print("=" * 80)
    print("DataFrame Structure Analysis")
    print("=" * 80)

    company = Company("AAPL")
    financials = company.get_financials()
    income_stmt = financials.income_statement()

    df = income_stmt.to_dataframe()

    print("\n1. DataFrame Info:")
    print("-" * 80)
    print(f"   Shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")
    print(f"   Index type: {type(df.index)}")
    print(f"   Index: {list(df.index)[:5]}...")

    print("\n2. First 15 Rows:")
    print("-" * 80)
    print(df.head(15))

    print("\n3. Check 'concept' column:")
    print("-" * 80)
    if "concept" in df.columns:
        concepts = df["concept"].tolist()
        print(f"   First 10 concepts: {concepts[:10]}")

        # Look for revenue-related concepts
        revenue_concepts = [c for c in concepts if "revenue" in str(c).lower()]
        print(f"\n   Revenue-related concepts: {revenue_concepts[:5]}")

        # Look for net income concepts
        income_concepts = [c for c in concepts if "income" in str(c).lower()]
        print(f"\n   Income-related concepts: {income_concepts[:5]}")

    print("\n4. Check 'label' column:")
    print("-" * 80)
    if "label" in df.columns:
        labels = df["label"].tolist()
        print(f"   First 10 labels: {labels[:10]}")

    print("\n5. How to access data by concept:")
    print("-" * 80)

    # Try to filter by concept
    if "concept" in df.columns:
        revenue_rows = df[df["concept"].str.contains("Revenues", case=False, na=False)]
        print("   Rows with 'Revenues' in concept:")
        print(revenue_rows)

    print("\n6. Comparison with getter methods:")
    print("-" * 80)
    print(f"   get_revenue(): {financials.get_revenue():,.0f}")
    print(f"   get_net_income(): {financials.get_net_income():,.0f}")

    # Try to find these values in the DataFrame
    if "concept" in df.columns:
        # Get the latest period column (last column that's not concept/label)
        date_cols = [c for c in df.columns if c not in ["concept", "label"]]
        if date_cols:
            latest_date = date_cols[-1]
            print(f"\n   Latest date column: {latest_date}")

            # Try to find revenue
            revenue_row = df[df["concept"].str.contains("revenue", case=False, na=False)]
            if not revenue_row.empty:
                print("\n   Revenue concepts found:")
                for idx, row in revenue_row.iterrows():
                    print(f"      {row['concept']}: {row[latest_date]:,.0f if row[latest_date] else 'N/A'}")

    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("\n1. DataFrame structure:")
    print("   - Rows: Individual line items from financial statement")
    print("   - Columns: 'concept' (XBRL tag), 'label' (human name), date columns")
    print("   - Access pattern: df[df['concept'] == 'FieldName'][date_column]")

    print("\n2. Easier approach for screening:")
    print("   - Use getter methods: get_revenue(), get_net_income(), etc.")
    print("   - EdgarTools handles field mapping internally")
    print("   - Returns latest value as float (perfect for screening)")

    print("\n3. For advanced analysis:")
    print("   - Use .to_dataframe() to get time series")
    print("   - Filter by 'concept' or 'label' columns")
    print("   - Access historical data for CAGR calculations")


if __name__ == "__main__":
    main()
