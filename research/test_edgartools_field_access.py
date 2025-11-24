"""
Deep dive: Test EdgarTools field access patterns

Purpose: Determine actual field names and whether field mapper is needed.
"""

import logging

from edgar import Company, set_identity

logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)

# Test with just one company for deep inspection
TEST_TICKER = "AAPL"


def main():
    """Test detailed field access patterns."""
    set_identity("research@example.com")

    print("=" * 60)
    print(f"Deep Field Access Test: {TEST_TICKER}")
    print("=" * 60)

    company = Company(TEST_TICKER)
    financials = company.get_financials()

    print(f"\n1. Company: {company.name}")
    print(f"   CIK: {company.cik}")

    # Test income statement access
    print("\n2. Income Statement Access:")
    print("-" * 60)

    income_stmt = financials.income_statement()  # Call as method!
    print(f"   Type: {type(income_stmt)}")
    print(f"   Shape: {income_stmt.shape if hasattr(income_stmt, 'shape') else 'N/A'}")

    # Try to get data
    print("\n   A. Using getter methods:")
    revenue = financials.get_revenue()
    net_income = financials.get_net_income()
    print(f"      get_revenue(): {type(revenue)}")
    print(f"      Latest revenue: {revenue.iloc[-1] if hasattr(revenue, 'iloc') else revenue}")
    print(f"      get_net_income(): {type(net_income)}")
    print(f"      Latest net income: {net_income.iloc[-1] if hasattr(net_income, 'iloc') else net_income}")

    # Inspect DataFrame structure
    print("\n   B. DataFrame structure:")
    if hasattr(income_stmt, "columns"):
        print(f"      Columns: {list(income_stmt.columns)[:5]}...")
    if hasattr(income_stmt, "index"):
        print(f"      Index (field names): {list(income_stmt.index)[:10]}")

    # Try to access specific fields
    print("\n   C. Field access patterns:")

    # Try different access methods
    test_fields = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "NetIncomeLoss",
        "OperatingIncomeLoss",
    ]

    for field in test_fields:
        # Try loc access (if it's a DataFrame with fields as index)
        if hasattr(income_stmt, "loc"):
            try:
                value = income_stmt.loc[field]
                print(f"      ✓ income_stmt.loc['{field}'] = {value.iloc[-1] if hasattr(value, 'iloc') else value}")
            except KeyError:
                print(f"      ✗ income_stmt.loc['{field}'] - not found")

    # Test balance sheet access
    print("\n3. Balance Sheet Access:")
    print("-" * 60)

    balance_sheet = financials.balance_sheet()  # Call as method!
    print(f"   Type: {type(balance_sheet)}")

    print("\n   A. Using getter methods:")
    total_assets = financials.get_total_assets()
    stockholders_equity = financials.get_stockholders_equity()
    print(f"      get_total_assets(): {total_assets.iloc[-1] if hasattr(total_assets, 'iloc') else total_assets}")
    print(
        f"      get_stockholders_equity(): {stockholders_equity.iloc[-1] if hasattr(stockholders_equity, 'iloc') else stockholders_equity}"
    )

    print("\n   B. DataFrame structure:")
    if hasattr(balance_sheet, "index"):
        print(f"      Index (field names): {list(balance_sheet.index)[:10]}")

    # Test other helper methods
    print("\n4. Other Helper Methods:")
    print("-" * 60)

    try:
        operating_cf = financials.get_operating_cash_flow()
        print(
            f"   get_operating_cash_flow(): {operating_cf.iloc[-1] if hasattr(operating_cf, 'iloc') else operating_cf}"
        )
    except Exception as e:
        print(f"   get_operating_cash_flow(): Failed - {e}")

    try:
        free_cf = financials.get_free_cash_flow()
        print(f"   get_free_cash_flow(): {free_cf.iloc[-1] if hasattr(free_cf, 'iloc') else free_cf}")
    except Exception as e:
        print(f"   get_free_cash_flow(): Failed - {e}")

    # Check if we can calculate ROE directly
    print("\n5. Can we calculate metrics directly?")
    print("-" * 60)

    try:
        # ROE = Net Income / Stockholders Equity
        # Note: getter methods return floats (latest value)
        roe = net_income / stockholders_equity
        print(f"   ROE (latest): {roe:.2%}")
        print("   ✓ Can calculate ROE directly using getter methods")
    except Exception as e:
        print(f"   ✗ ROE calculation failed: {e}")

    # Test if XBRL tags are exposed
    print("\n6. XBRL Access (raw tags):")
    print("-" * 60)

    if hasattr(financials, "xb"):
        print("   ✓ financials.xb exists (XBRL object)")
        xb = financials.xb
        print(f"   Type: {type(xb)}")

        # Try to access facts
        if hasattr(xb, "facts"):
            print("   ✓ XBRL facts accessible")
            facts = xb.facts
            print(f"   Facts type: {type(facts)}")
            if hasattr(facts, "keys"):
                print(f"   Sample fact keys: {list(facts.keys())[:5]}")
        else:
            print("   ✗ No .facts attribute")
    else:
        print("   ✗ No .xb attribute")

    # Final assessment
    print("\n" + "=" * 60)
    print("ASSESSMENT")
    print("=" * 60)

    print("\n✓ EdgarTools provides:")
    print("  1. Convenient getter methods (get_revenue, get_net_income, etc.)")
    print("  2. Direct access to statement DataFrames")
    print("  3. Fields accessible via DataFrame .loc[field_name]")

    print("\n❓ QUESTIONS:")
    print("  1. Are XBRL tag names consistent across companies?")
    print("  2. Do we need field mapper for variations, or are tags standardized?")
    print("  3. Can all required metrics be calculated using getter methods?")

    print("\n📋 RECOMMENDATION:")
    print("  - Test with 5 more companies to see tag name variations")
    print("  - If tags consistent: Field mapper NOT needed")
    print("  - If tags vary: Field mapper IS needed")


if __name__ == "__main__":
    main()
