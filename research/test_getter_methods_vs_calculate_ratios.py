"""
Compare EdgarTools getter methods vs calculate_ratios() for ratio calculations

Key Question: Should we:
A) Use getter methods + custom ratio calculations
B) Use calculate_ratios() + analyze_trends()
C) Hybrid approach
"""

from edgar import Company, set_identity

set_identity("Research research@example.com")


def compare_approaches(ticker: str):
    """Compare getter methods vs calculate_ratios approaches"""
    print(f"\n{'=' * 80}")
    print(f"{ticker} - Comparing Getter Methods vs Built-in Ratios")
    print(f"{'=' * 80}")

    company = Company(ticker)

    # Approach A: Getter Methods (from Financials object)
    print("\n--- Approach A: Getter Methods (Recommended from Prior Research) ---")
    try:
        financials = company.get_financials()

        revenue = financials.get_revenue()
        net_income = financials.get_net_income()
        total_assets = financials.get_total_assets()
        stockholders_equity = financials.get_stockholders_equity()
        operating_cash_flow = financials.get_operating_cash_flow()
        free_cash_flow = financials.get_free_cash_flow()
        current_assets = financials.get_current_assets()
        current_liabilities = financials.get_current_liabilities()

        print(f"✅ Revenue: ${revenue:,.0f}")
        print(f"✅ Net Income: ${net_income:,.0f}")
        print(f"✅ Total Assets: ${total_assets:,.0f}")
        print(f"✅ Stockholders' Equity: ${stockholders_equity:,.0f}")
        print(f"✅ Operating Cash Flow: ${operating_cash_flow:,.0f}")
        print(f"✅ Free Cash Flow: ${free_cash_flow:,.0f}")
        print(f"✅ Current Assets: ${current_assets:,.0f}")
        print(f"✅ Current Liabilities: ${current_liabilities:,.0f}")

        # Calculate ratios manually
        print("\n--- Manual Ratio Calculations ---")
        net_margin = (net_income / revenue) if revenue else None
        roe = (net_income / stockholders_equity) if stockholders_equity else None
        roa = (net_income / total_assets) if total_assets else None
        current_ratio = (current_assets / current_liabilities) if current_liabilities else None

        print(f"Net Margin: {net_margin:.4f} ({net_margin * 100:.2f}%)" if net_margin else "N/A")
        print(f"ROE: {roe:.4f} ({roe * 100:.2f}%)" if roe else "N/A")
        print(f"ROA: {roa:.4f} ({roa * 100:.2f}%)" if roa else "N/A")
        print(f"Current Ratio: {current_ratio:.2f}" if current_ratio else "N/A")

        getter_results = {
            "revenue": revenue,
            "net_income": net_income,
            "net_margin": net_margin,
            "roe": roe,
            "roa": roa,
            "current_ratio": current_ratio,
        }

    except Exception as e:
        print(f"❌ Error with getter methods: {e}")
        getter_results = {}

    # Approach B: calculate_ratios() on Statement objects
    print("\n--- Approach B: Built-in calculate_ratios() ---")
    try:
        tenk = company.get_filings(form="10-K").latest(1)
        financials_obj = tenk.obj()

        income_stmt = financials_obj.income_statement
        balance_sheet = financials_obj.balance_sheet

        income_ratios = income_stmt.calculate_ratios()
        balance_ratios = balance_sheet.calculate_ratios()

        print(f"Income Statement Ratios: {income_ratios}")
        print(f"Balance Sheet Ratios: {balance_ratios}")

        builtin_results = {"income_ratios": income_ratios, "balance_ratios": balance_ratios}

    except Exception as e:
        print(f"❌ Error with calculate_ratios: {e}")
        builtin_results = {}

    # Comparison
    print("\n--- Comparison ---")
    if getter_results and builtin_results:
        if "net_margin" in builtin_results.get("income_ratios", {}):
            getter_net_margin = getter_results.get("net_margin")
            builtin_net_margin = builtin_results["income_ratios"]["net_margin"]
            print(f"Net Margin - Getter: {getter_net_margin:.4f}, Built-in: {builtin_net_margin:.4f}")
            print(f"Match: {abs(getter_net_margin - builtin_net_margin) < 0.0001}")
        else:
            print("Built-in calculate_ratios() returned NO net_margin")
            print(f"Getter methods calculated net_margin: {getter_results.get('net_margin', 'N/A')}")

    return {"ticker": ticker, "getter_results": getter_results, "builtin_results": builtin_results}


if __name__ == "__main__":
    results = []
    for ticker in ["AAPL", "JPM", "JNJ", "XOM", "WMT"]:
        result = compare_approaches(ticker)
        results.append(result)

    # Summary
    print(f"\n\n{'=' * 80}")
    print("SUMMARY: Getter Methods vs Built-in Ratios")
    print(f"{'=' * 80}")

    getter_success = sum(1 for r in results if r.get("getter_results"))
    builtin_success = sum(1 for r in results if r.get("builtin_results", {}).get("income_ratios"))

    print(f"\nGetter Methods Success: {getter_success}/5 companies")
    print(f"Built-in calculate_ratios() Success: {builtin_success}/5 companies returned data")

    # Count how many companies got net_margin from built-in
    builtin_net_margin_count = sum(
        1 for r in results if r.get("builtin_results", {}).get("income_ratios", {}).get("net_margin")
    )
    print(f"Built-in calculate_ratios() returned net_margin: {builtin_net_margin_count}/5 companies")

    print("\n--- RECOMMENDATION ---")
    print("Based on coverage:")
    if getter_success >= 4:
        print("✅ USE GETTER METHODS + MANUAL RATIO CALCULATIONS")
        print("   - 100% coverage with getter methods")
        print("   - calculate_ratios() has limited/inconsistent coverage")
        print("   - We need to build custom MetricsCalculator anyway")
    else:
        print("❓ Need more investigation")
