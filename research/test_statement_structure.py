"""
Inspect EdgarTools Statement object structure

Purpose: Understand how to access individual fields from Statement objects
"""

import logging

from edgar import Company, set_identity

logging.basicConfig(level=logging.WARNING)

TEST_TICKER = "AAPL"


def main():
    """Inspect Statement structure."""
    set_identity("research@example.com")

    print("=" * 80)
    print(f"Statement Structure Inspection: {TEST_TICKER}")
    print("=" * 80)

    company = Company(TEST_TICKER)
    financials = company.get_financials()

    # Get income statement
    income_stmt = financials.income_statement()

    print("\n1. Statement Object Type & Attributes:")
    print("-" * 80)
    print(f"   Type: {type(income_stmt)}")
    print(f"   Attributes: {[a for a in dir(income_stmt) if not a.startswith('_')][:20]}")

    # Try to convert to DataFrame
    print("\n2. Can we convert to DataFrame?")
    print("-" * 80)

    if hasattr(income_stmt, "to_dataframe"):
        df = income_stmt.to_dataframe()
        print("   ✓ to_dataframe() works!")
        print(f"   Type: {type(df)}")
        print(f"   Shape: {df.shape}")
        print("\n   First 10 field names (index):")
        for i, field in enumerate(list(df.index)[:10]):
            print(f"      {i + 1}. {field}")

        # Show sample data (first 3 columns)
        print(f"\n   Columns (dates): {list(df.columns)[:3]}...")

        # Try to access specific fields
        print("\n   Sample field access:")
        test_fields = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "NetIncomeLoss",
            "OperatingIncomeLoss",
            "GrossProfit",
        ]

        for field in test_fields:
            try:
                value = df.loc[field]
                print(f"      ✓ df.loc['{field}']:")
                print(f"         Latest: {value.iloc[-1]:,.0f}")
            except KeyError:
                print(f"      ✗ df.loc['{field}'] - not found")

    elif hasattr(income_stmt, "get_dataframe"):
        df = income_stmt.get_dataframe()
        print("   ✓ get_dataframe() works!")
        print(f"   Type: {type(df)}")
        print(f"   Shape: {df.shape}")
        print(f"   Index: {list(df.index)[:10]}")

    else:
        print("   ✗ No dataframe conversion method found")
        print(f"   Available methods: {[m for m in dir(income_stmt) if not m.startswith('_')]}")

    # Test with multiple companies
    print("\n" + "=" * 80)
    print("3. Cross-Company Field Name Consistency Test")
    print("=" * 80)

    test_tickers = ["MSFT", "JPM", "JNJ"]

    for ticker in test_tickers:
        print(f"\n   {ticker}:")
        try:
            comp = Company(ticker)
            fins = comp.get_financials()
            inc = fins.income_statement()

            if hasattr(inc, "to_dataframe"):
                df = inc.to_dataframe()
                fields = list(df.index)
                print(f"      Total fields: {len(fields)}")

                # Check for common fields
                common_fields = {
                    "Revenues": "Revenues" in fields,
                    "RevenueFromContract...": any("RevenueFromContract" in f for f in fields),
                    "NetIncomeLoss": "NetIncomeLoss" in fields,
                    "OperatingIncomeLoss": "OperatingIncomeLoss" in fields,
                }

                for field_name, exists in common_fields.items():
                    symbol = "✓" if exists else "✗"
                    print(f"      {symbol} {field_name}")

        except Exception as e:
            print(f"      ✗ Error: {e}")

    print("\n" + "=" * 80)
    print("FINDINGS:")
    print("=" * 80)
    print("\n1. EdgarTools Statement objects have .to_dataframe() method")
    print("2. DataFrame has XBRL field names as index")
    print("3. Field names need to be tested for consistency across companies")
    print("\n4. For screening, we can likely use:")
    print("   - Getter methods (get_revenue, get_net_income, etc.)")
    print("   - OR Statement.to_dataframe() + field name mapping")
    print("\n5. Decision:")
    print("   - If field names are consistent: Use direct .loc[] access")
    print("   - If field names vary: Need FieldMapper")


if __name__ == "__main__":
    main()
