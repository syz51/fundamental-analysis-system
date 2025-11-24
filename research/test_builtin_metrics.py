"""
Test EdgarTools Built-in Ratio/Trend Methods

Research Question: Can we use EdgarTools' built-in methods instead of custom MetricsCalculator?

Tests:
1. get_financial_metrics() - What metrics are available?
2. calculate_ratios() - What ratios are provided?
3. analyze_trends() - Can it calculate CAGR?

Test Companies (5 diverse sectors):
- AAPL (Tech)
- JPM (Bank)
- JNJ (Healthcare)
- XOM (Energy)
- WMT (Consumer)

Screening Metrics Needed:
- Revenue (latest)
- Net Income (latest)
- Revenue CAGR (10Y, 5Y)
- Operating Margin (3Y avg)
- Net Margin (3Y avg)
- ROE (3Y avg)
- ROA (3Y avg)
- ROIC (3Y avg)
- Debt/Equity
- Current Ratio
"""

import json
from typing import Any

from edgar import Company, set_identity

# Set SEC identity (required for API access)
set_identity("Your Name your.email@example.com")

# Test companies
TEST_COMPANIES = {
    "AAPL": "Apple Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "JNJ": "Johnson & Johnson",
    "XOM": "Exxon Mobil Corporation",
    "WMT": "Walmart Inc.",
}


def test_get_financial_metrics(ticker: str) -> dict[str, Any]:
    """Test get_financial_metrics() method"""
    print(f"\n{'=' * 80}")
    print(f"Testing get_financial_metrics() for {ticker}")
    print(f"{'=' * 80}")

    try:
        company = Company(ticker)
        financials = company.financials

        # Try to call get_financial_metrics() if it exists
        if hasattr(financials, "get_financial_metrics"):
            metrics = financials.get_financial_metrics()
            print("\n✅ get_financial_metrics() exists!")
            print(f"Type: {type(metrics)}")
            print("\nMetrics returned:")
            print(metrics)
            return {"exists": True, "data": str(metrics), "type": str(type(metrics))}
        else:
            print("\n❌ get_financial_metrics() does NOT exist")
            return {"exists": False}

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"error": str(e)}


def test_calculate_ratios(ticker: str) -> dict[str, Any]:
    """Test calculate_ratios() on income statement and balance sheet"""
    print(f"\n{'=' * 80}")
    print(f"Testing calculate_ratios() for {ticker}")
    print(f"{'=' * 80}")

    try:
        company = Company(ticker)
        tenk = company.get_filings(form="10-K").latest(1)

        # Try income statement ratios
        print("\n--- Income Statement Ratios ---")
        financials = tenk.obj()
        income_stmt = financials.income_statement

        if hasattr(income_stmt, "calculate_ratios"):
            ratios = income_stmt.calculate_ratios()
            print("✅ income_statement.calculate_ratios() exists!")
            print(f"Type: {type(ratios)}")
            print("\nRatios returned:")
            print(ratios)
            income_result = {"exists": True, "data": str(ratios), "type": str(type(ratios))}
        else:
            print("❌ income_statement.calculate_ratios() does NOT exist")
            income_result = {"exists": False}

        # Try balance sheet ratios
        print("\n--- Balance Sheet Ratios ---")
        balance_sheet = financials.balance_sheet

        if hasattr(balance_sheet, "calculate_ratios"):
            ratios = balance_sheet.calculate_ratios()
            print("✅ balance_sheet.calculate_ratios() exists!")
            print(f"Type: {type(ratios)}")
            print("\nRatios returned:")
            print(ratios)
            balance_result = {"exists": True, "data": str(ratios), "type": str(type(ratios))}
        else:
            print("❌ balance_sheet.calculate_ratios() does NOT exist")
            balance_result = {"exists": False}

        return {"income_statement": income_result, "balance_sheet": balance_result}

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"error": str(e)}


def test_analyze_trends(ticker: str) -> dict[str, Any]:
    """Test analyze_trends() method"""
    print(f"\n{'=' * 80}")
    print(f"Testing analyze_trends() for {ticker}")
    print(f"{'=' * 80}")

    try:
        company = Company(ticker)
        tenk = company.get_filings(form="10-K").latest(1)
        financials = tenk.obj()

        # Try on income statement
        print("\n--- Income Statement Trends ---")
        income_stmt = financials.income_statement

        if hasattr(income_stmt, "analyze_trends"):
            trends = income_stmt.analyze_trends()
            print("✅ income_statement.analyze_trends() exists!")
            print(f"Type: {type(trends)}")
            print("\nTrends returned:")
            print(trends)
            income_result = {"exists": True, "data": str(trends), "type": str(type(trends))}
        else:
            print("❌ income_statement.analyze_trends() does NOT exist")
            income_result = {"exists": False}

        # Try on balance sheet
        print("\n--- Balance Sheet Trends ---")
        balance_sheet = financials.balance_sheet

        if hasattr(balance_sheet, "analyze_trends"):
            trends = balance_sheet.analyze_trends()
            print("✅ balance_sheet.analyze_trends() exists!")
            print(f"Type: {type(trends)}")
            print("\nTrends returned:")
            print(trends)
            balance_result = {"exists": True, "data": str(trends), "type": str(type(trends))}
        else:
            print("❌ balance_sheet.analyze_trends() does NOT exist")
            balance_result = {"exists": False}

        return {"income_statement": income_result, "balance_sheet": balance_result}

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"error": str(e)}


def explore_available_methods(ticker: str) -> dict[str, Any]:
    """Explore what methods are actually available on financials and statements"""
    print(f"\n{'=' * 80}")
    print(f"Exploring Available Methods for {ticker}")
    print(f"{'=' * 80}")

    try:
        company = Company(ticker)
        tenk = company.get_filings(form="10-K").latest(1)
        financials = tenk.obj()

        # Check financials object
        print("\n--- Methods on Financials Object ---")
        financials_methods = [m for m in dir(financials) if not m.startswith("_")]
        print(f"Available methods: {financials_methods}")

        # Check income statement
        print("\n--- Methods on Income Statement ---")
        income_stmt = financials.income_statement
        income_methods = [m for m in dir(income_stmt) if not m.startswith("_")]
        print(f"Available methods: {income_methods}")

        # Check balance sheet
        print("\n--- Methods on Balance Sheet ---")
        balance_sheet = financials.balance_sheet
        balance_methods = [m for m in dir(balance_sheet) if not m.startswith("_")]
        print(f"Available methods: {balance_methods}")

        # Check cash flow
        print("\n--- Methods on Cash Flow Statement ---")
        cash_flow = financials.cash_flow_statement
        cash_flow_methods = [m for m in dir(cash_flow) if not m.startswith("_")]
        print(f"Available methods: {cash_flow_methods}")

        return {
            "financials": financials_methods,
            "income_statement": income_methods,
            "balance_sheet": balance_methods,
            "cash_flow_statement": cash_flow_methods,
        }

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return {"error": str(e)}


def main():
    """Run all tests"""
    results = {}

    for ticker, name in TEST_COMPANIES.items():
        print(f"\n\n{'#' * 80}")
        print(f"# {ticker} - {name}")
        print(f"{'#' * 80}")

        company_results = {
            "name": name,
            "explore_methods": explore_available_methods(ticker),
            "get_financial_metrics": test_get_financial_metrics(ticker),
            "calculate_ratios": test_calculate_ratios(ticker),
            "analyze_trends": test_analyze_trends(ticker),
        }

        results[ticker] = company_results

    # Save results to JSON
    output_file = "research/FINDINGS_builtin_metrics_raw.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n\n{'=' * 80}")
    print(f"Results saved to {output_file}")
    print(f"{'=' * 80}")

    # Print summary
    print("\n\nSUMMARY")
    print(f"{'=' * 80}")
    for ticker in TEST_COMPANIES:
        print(f"\n{ticker}:")
        print(f"  get_financial_metrics: {results[ticker]['get_financial_metrics'].get('exists', 'error')}")
        print(
            f"  calculate_ratios (income): {results[ticker]['calculate_ratios'].get('income_statement', {}).get('exists', 'error')}"
        )
        print(
            f"  calculate_ratios (balance): {results[ticker]['calculate_ratios'].get('balance_sheet', {}).get('exists', 'error')}"
        )
        print(
            f"  analyze_trends (income): {results[ticker]['analyze_trends'].get('income_statement', {}).get('exists', 'error')}"
        )
        print(
            f"  analyze_trends (balance): {results[ticker]['analyze_trends'].get('balance_sheet', {}).get('exists', 'error')}"
        )


if __name__ == "__main__":
    main()
