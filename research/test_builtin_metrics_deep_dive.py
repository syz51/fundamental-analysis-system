"""
Deep Dive: Why do calculate_ratios() and analyze_trends() return empty dicts?

Investigation:
1. Inspect method signatures (parameters, defaults)
2. Look at underlying DataFrame structure
3. Test with different parameters
4. Check if data is available but methods need different input
"""

import inspect

from edgar import Company, set_identity

# Set SEC identity
set_identity("Research research@example.com")


def inspect_method_signature(obj, method_name: str):
    """Print method signature and docstring"""
    if hasattr(obj, method_name):
        method = getattr(obj, method_name)
        print(f"\n--- {method_name} Signature ---")
        print(f"Signature: {inspect.signature(method)}")
        print(f"Docstring:\n{inspect.getdoc(method)}")

        # Try to get source code
        try:
            source = inspect.getsource(method)
            print("\nSource Code (first 50 lines):\n")
            print("\n".join(source.split("\n")[:50]))
        except Exception as e:
            print(f"Could not get source: {e}")
    else:
        print(f"\n❌ {method_name} does not exist")


def deep_dive_ticker(ticker: str):
    """Deep dive investigation for a single ticker"""
    print(f"\n{'#' * 80}")
    print(f"# DEEP DIVE: {ticker}")
    print(f"{'#' * 80}")

    company = Company(ticker)
    tenk = company.get_filings(form="10-K").latest(1)
    financials = tenk.obj()

    # Get statements
    income_stmt = financials.income_statement
    balance_sheet = financials.balance_sheet

    # 1. Inspect calculate_ratios signature
    print(f"\n{'=' * 80}")
    print("1. INSPECTING calculate_ratios()")
    print(f"{'=' * 80}")
    inspect_method_signature(income_stmt, "calculate_ratios")

    # 2. Inspect analyze_trends signature
    print(f"\n{'=' * 80}")
    print("2. INSPECTING analyze_trends()")
    print(f"{'=' * 80}")
    inspect_method_signature(income_stmt, "analyze_trends")

    # 3. Look at underlying DataFrame
    print(f"\n{'=' * 80}")
    print("3. UNDERLYING DATA STRUCTURE")
    print(f"{'=' * 80}")

    print("\n--- Income Statement DataFrame ---")
    df = income_stmt.to_dataframe()
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 10 rows:")
    print(df.head(10))

    print("\n--- Balance Sheet DataFrame ---")
    df_bs = balance_sheet.to_dataframe()
    print(f"Shape: {df_bs.shape}")
    print(f"Columns: {list(df_bs.columns)}")
    print("\nFirst 10 rows:")
    print(df_bs.head(10))

    # 4. Try calling methods with different parameters
    print(f"\n{'=' * 80}")
    print("4. TESTING DIFFERENT PARAMETERS")
    print(f"{'=' * 80}")

    # Check if methods accept parameters
    sig = inspect.signature(income_stmt.calculate_ratios)
    params = sig.parameters
    print(f"\ncalculate_ratios parameters: {list(params.keys())}")

    sig_trends = inspect.signature(income_stmt.analyze_trends)
    params_trends = sig_trends.parameters
    print(f"analyze_trends parameters: {list(params_trends.keys())}")

    # 5. Test actual calls
    print(f"\n{'=' * 80}")
    print("5. TESTING ACTUAL CALLS")
    print(f"{'=' * 80}")

    print("\n--- Income Statement calculate_ratios() ---")
    ratios = income_stmt.calculate_ratios()
    print(f"Result: {ratios}")
    print(f"Type: {type(ratios)}")
    print(f"Length: {len(ratios) if isinstance(ratios, dict) else 'N/A'}")

    print("\n--- Income Statement analyze_trends() ---")
    trends = income_stmt.analyze_trends()
    print(f"Result: {trends}")
    print(f"Type: {type(trends)}")
    print(f"Length: {len(trends) if isinstance(trends, dict) else 'N/A'}")

    # 6. Check for other useful methods
    print(f"\n{'=' * 80}")
    print("6. OTHER POTENTIALLY USEFUL METHODS")
    print(f"{'=' * 80}")

    all_methods = [m for m in dir(income_stmt) if not m.startswith("_") and callable(getattr(income_stmt, m))]
    print("\nAll callable methods on income statement:")
    for method in all_methods:
        print(f"  - {method}")

    # 7. Try to manually calculate ratios from DataFrame
    print(f"\n{'=' * 80}")
    print("7. MANUAL RATIO CALCULATION FROM DATAFRAME")
    print(f"{'=' * 80}")

    print("\nTrying to extract Revenue and Net Income from DataFrame:")

    # Look for revenue-related concepts
    revenue_concepts = [
        "Revenues",
        "Revenue",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "RevenueFromContractWithCustomer",
    ]

    for concept in revenue_concepts:
        if concept in df.index:
            print(f"\n✅ Found concept: {concept}")
            print(df.loc[concept])

    # Look for net income concepts
    ni_concepts = ["NetIncomeLoss", "NetIncome", "ProfitLoss"]

    for concept in ni_concepts:
        if concept in df.index:
            print(f"\n✅ Found concept: {concept}")
            print(df.loc[concept])


if __name__ == "__main__":
    # Start with one company that returned some data (XOM)
    # Then test one that returned empty (AAPL)

    print("\n" + "=" * 80)
    print("TESTING XOM (returned net_margin)")
    print("=" * 80)
    deep_dive_ticker("XOM")

    print("\n\n" + "=" * 80)
    print("TESTING AAPL (returned empty dict)")
    print("=" * 80)
    deep_dive_ticker("AAPL")
