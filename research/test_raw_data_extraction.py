"""
Test get_raw_data() to understand what data is available for ratio calculations
"""

from edgar import Company, set_identity

set_identity("Research research@example.com")


def test_raw_data(ticker: str):
    """Test get_raw_data() method"""
    print(f"\n{'=' * 80}")
    print(f"{ticker} - get_raw_data() Analysis")
    print(f"{'=' * 80}")

    company = Company(ticker)
    tenk = company.get_filings(form="10-K").latest(1)
    financials = tenk.obj()

    # Income Statement
    print("\n--- Income Statement get_raw_data() ---")
    income_stmt = financials.income_statement
    raw_data = income_stmt.get_raw_data()
    print(f"Type: {type(raw_data)}")
    print(f"Keys: {list(raw_data.keys()) if isinstance(raw_data, dict) else 'N/A'}")
    print("\nRaw data:")
    for key, value in raw_data.items() if isinstance(raw_data, dict) else []:
        print(f"  {key}: {value}")

    # Try to inspect _calculate_income_statement_ratios
    print("\n--- Trying to see what ratios are calculated ---")
    ratios = income_stmt.calculate_ratios()
    print(f"Ratios returned: {ratios}")

    # Balance Sheet
    print("\n--- Balance Sheet get_raw_data() ---")
    balance_sheet = financials.balance_sheet
    raw_data_bs = balance_sheet.get_raw_data()
    print(f"Type: {type(raw_data_bs)}")
    print(f"Keys: {list(raw_data_bs.keys()) if isinstance(raw_data_bs, dict) else 'N/A'}")
    print("\nRaw data:")
    for key, value in raw_data_bs.items() if isinstance(raw_data_bs, dict) else []:
        print(f"  {key}: {value}")

    # Balance sheet ratios
    print("\n--- Balance Sheet Ratios ---")
    ratios_bs = balance_sheet.calculate_ratios()
    print(f"Ratios returned: {ratios_bs}")

    # Test getter methods (from previous research)
    print("\n--- Testing Getter Methods (Known to Work) ---")
    try:
        revenue = income_stmt.get_revenue()
        print(f"✅ get_revenue(): {revenue:,.0f}")
    except Exception as e:
        print(f"❌ get_revenue(): {e}")

    try:
        net_income = income_stmt.get_net_income()
        print(f"✅ get_net_income(): {net_income:,.0f}")
    except Exception as e:
        print(f"❌ get_net_income(): {e}")

    try:
        operating_income = income_stmt.get_operating_income()
        print(f"✅ get_operating_income(): {operating_income:,.0f}")
    except Exception as e:
        print(f"❌ get_operating_income(): {e}")

    try:
        total_assets = balance_sheet.get_total_assets()
        print(f"✅ get_total_assets(): {total_assets:,.0f}")
    except Exception as e:
        print(f"❌ get_total_assets(): {e}")

    try:
        total_equity = balance_sheet.get_stockholders_equity()
        print(f"✅ get_stockholders_equity(): {total_equity:,.0f}")
    except Exception as e:
        print(f"❌ get_stockholders_equity(): {e}")

    # Manual ratio calculation using getter methods
    print("\n--- Manual Ratio Calculations Using Getter Methods ---")
    try:
        revenue = income_stmt.get_revenue()
        net_income = income_stmt.get_net_income()
        operating_income = income_stmt.get_operating_income()
        total_assets = balance_sheet.get_total_assets()
        total_equity = balance_sheet.get_stockholders_equity()

        # Calculate ratios manually
        net_margin = (net_income / revenue) * 100 if revenue else None
        operating_margin = (operating_income / revenue) * 100 if revenue else None
        roe = (net_income / total_equity) * 100 if total_equity else None
        roa = (net_income / total_assets) * 100 if total_assets else None

        print(f"Net Margin: {net_margin:.2f}%" if net_margin else "N/A")
        print(f"Operating Margin: {operating_margin:.2f}%" if operating_margin else "N/A")
        print(f"ROE: {roe:.2f}%" if roe else "N/A")
        print(f"ROA: {roa:.2f}%" if roa else "N/A")

        # Compare with built-in
        print("\n--- Comparison with Built-in calculate_ratios() ---")
        print(f"Built-in net_margin: {ratios.get('net_margin', 'N/A')}")
        if net_margin and "net_margin" in ratios:
            print(f"Manual net_margin (as decimal): {net_margin / 100:.4f}")
            print(f"Match: {abs(ratios['net_margin'] - net_margin / 100) < 0.001}")

    except Exception as e:
        print(f"Error calculating manual ratios: {e}")


if __name__ == "__main__":
    # Test both companies
    test_raw_data("XOM")
    test_raw_data("AAPL")
    test_raw_data("JPM")
    test_raw_data("JNJ")
    test_raw_data("WMT")
