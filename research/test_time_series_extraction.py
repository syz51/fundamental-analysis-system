"""
Test Time Series Data Extraction for CAGR Calculations

Research Questions:
1. Are XBRL concept tags consistent across companies?
2. How to extract date columns reliably from DataFrame?
3. How many years of history available in latest 10-K?
4. Best approach: analyze_trends() vs manual extraction?

Test Companies (10 diverse):
- Tech: AAPL, MSFT, GOOGL
- Banks: JPM, BAC
- Consumer: WMT, PG
- Energy: XOM
- Healthcare: JNJ
- Recent IPO: SNOW (2020 IPO, <5Y history)
"""

import json
from datetime import datetime

import pandas as pd
from edgar import Company, set_identity

# Set SEC identity
set_identity("YourName your.email@example.com")

# Test companies
TEST_COMPANIES = {
    "Tech": ["AAPL", "MSFT", "GOOGL"],
    "Banks": ["JPM", "BAC"],
    "Consumer": ["WMT", "PG"],
    "Energy": ["XOM"],
    "Healthcare": ["JNJ"],
    "Recent IPO": ["SNOW"],  # 2020 IPO, <5Y history
}

FLAT_TICKERS = [ticker for tickers in TEST_COMPANIES.values() for ticker in tickers]


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate Compound Annual Growth Rate"""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def extract_date_columns(df: pd.DataFrame) -> list[str]:
    """
    Extract date columns from DataFrame, excluding metadata columns

    Returns chronologically sorted date column names
    """
    # Common metadata columns to exclude
    metadata_cols = ["label", "concept", "unit", "form", "filed", "frame"]

    # Get all columns that aren't metadata
    potential_date_cols = [col for col in df.columns if col not in metadata_cols]

    # Try to parse as dates and sort chronologically
    date_cols = []
    for col in potential_date_cols:
        try:
            # Try parsing column name as date
            pd.to_datetime(col)
            date_cols.append(col)
        except:
            # Not a date column, skip
            pass

    # Sort chronologically
    if date_cols:
        date_cols = sorted(date_cols)

    return date_cols


def test_company_time_series(ticker: str) -> dict:
    """
    Test time series extraction for a single company

    Returns dict with:
    - ticker
    - success (bool)
    - revenue_tag (XBRL concept used)
    - years_available (int)
    - date_columns (list)
    - revenue_values (dict: year -> value)
    - cagr_10y (float or None)
    - method_used (str: 'analyze_trends', 'manual_df', or 'getter')
    - errors (list)
    """
    result = {
        "ticker": ticker,
        "success": False,
        "revenue_tag": None,
        "years_available": 0,
        "date_columns": [],
        "revenue_values": {},
        "cagr_10y": None,
        "method_used": None,
        "errors": [],
    }

    try:
        print(f"\n{'=' * 60}")
        print(f"Testing: {ticker}")
        print(f"{'=' * 60}")

        # Get company and latest 10-K
        company = Company(ticker)
        filing = company.get_filings(form="10-K").latest(1)

        if not filing:
            result["errors"].append("No 10-K filing found")
            return result

        print(f"Filing: {filing.form} filed {filing.filing_date}")

        # Get TenK object
        tenk = filing.obj()

        # METHOD 1: Test if analyze_trends() exists on financials
        print("\n--- METHOD 1: analyze_trends() (if available) ---")
        try:
            if hasattr(tenk.financials, "analyze_trends"):
                trends = tenk.financials.analyze_trends()
                print(f"analyze_trends() available: {trends is not None}")
                if trends:
                    print(f"Trends type: {type(trends)}")
                    print(f"Trends keys: {trends.keys() if isinstance(trends, dict) else 'N/A'}")
                else:
                    result["errors"].append("analyze_trends() returned None")
            else:
                result["errors"].append("analyze_trends() not available")
        except Exception as e:
            result["errors"].append(f"analyze_trends() error: {e!s}")
            print(f"Error: {e}")

        # METHOD 2: Test manual DataFrame extraction from Statement object
        print("\n--- METHOD 2: Manual DataFrame Extraction from Statement ---")
        try:
            # Get income statement Statement object and convert to DataFrame
            income_stmt = tenk.income_statement.to_dataframe()
            print(f"Income statement type: {type(income_stmt)}")

            if income_stmt is not None:
                # Check if it's a DataFrame
                if isinstance(income_stmt, pd.DataFrame):
                    print(f"DataFrame shape: {income_stmt.shape}")
                    print(f"Columns: {list(income_stmt.columns)}")

                    # Extract date columns
                    date_cols = extract_date_columns(income_stmt)
                    result["date_columns"] = date_cols
                    result["years_available"] = len(date_cols)

                    print(f"Date columns found: {len(date_cols)}")
                    if date_cols:
                        print(f"Date range: {date_cols[0]} to {date_cols[-1]}")

                    # Try to find revenue row
                    # Common revenue concepts
                    revenue_concepts = [
                        "Revenues",
                        "Revenue",
                        "RevenueFromContractWithCustomerExcludingAssessedTax",
                        "SalesRevenueNet",
                        "RevenueFromContractWithCustomer",
                    ]

                    revenue_row = None
                    revenue_tag = None

                    # Check if 'label' column exists
                    if "label" in income_stmt.columns:
                        # Get all rows with 'revenue' in label
                        revenue_matches = income_stmt[
                            income_stmt["label"].str.contains("revenue", case=False, na=False)
                        ]

                        if not revenue_matches.empty:
                            # Filter out rows where all date columns are NaN (abstract headers)
                            valid_matches = revenue_matches[revenue_matches[date_cols].notna().any(axis=1)]

                            if not valid_matches.empty:
                                # Prefer rows with simpler labels (shorter, or containing "total")
                                # First try to find "Total" revenue
                                total_matches = valid_matches[
                                    valid_matches["label"].str.contains("total", case=False, na=False)
                                ]
                                if not total_matches.empty:
                                    revenue_row = total_matches.iloc[0]
                                    revenue_tag = revenue_row["label"]
                                else:
                                    # Otherwise, prefer shorter labels (likely more general)
                                    # Sort by label length and take first
                                    valid_matches = valid_matches.copy()
                                    valid_matches["label_len"] = valid_matches["label"].str.len()
                                    valid_matches = valid_matches.sort_values("label_len")
                                    revenue_row = valid_matches.iloc[0]
                                    revenue_tag = revenue_row["label"]

                    # Try 'concept' column if label didn't work
                    if revenue_row is None and "concept" in income_stmt.columns:
                        for concept in revenue_concepts:
                            matches = income_stmt[income_stmt["concept"].str.contains(concept, case=False, na=False)]
                            if not matches.empty:
                                # Filter out NaN rows
                                valid_matches = matches[matches[date_cols].notna().any(axis=1)]
                                if not valid_matches.empty:
                                    revenue_row = valid_matches.iloc[0]
                                    revenue_tag = concept
                                    break

                    if revenue_row is not None:
                        result["revenue_tag"] = revenue_tag
                        print(f"Revenue tag: {revenue_tag}")

                        # Extract revenue values for all date columns
                        revenue_values = {}
                        for col in date_cols:
                            val = revenue_row[col]
                            if pd.notna(val):
                                revenue_values[col] = float(val)

                        result["revenue_values"] = revenue_values
                        print(f"Revenue values extracted: {len(revenue_values)} years")

                        # Calculate 10Y CAGR if possible
                        if len(revenue_values) >= 2:
                            years_list = sorted(revenue_values.keys())
                            oldest_year = years_list[0]
                            newest_year = years_list[-1]

                            # Parse years to calculate duration
                            try:
                                oldest_date = pd.to_datetime(oldest_year)
                                newest_date = pd.to_datetime(newest_year)
                                years_diff = (newest_date - oldest_date).days / 365.25

                                if years_diff > 0:
                                    cagr = calculate_cagr(
                                        revenue_values[oldest_year], revenue_values[newest_year], years_diff
                                    )
                                    result["cagr_10y"] = cagr
                                    result["success"] = True
                                    result["method_used"] = "manual_df"

                                    print(f"CAGR ({years_diff:.1f}Y): {cagr:.2f}%")
                                    print(f"  {oldest_year}: ${revenue_values[oldest_year]:,.0f}")
                                    print(f"  {newest_year}: ${revenue_values[newest_year]:,.0f}")
                            except Exception as e:
                                result["errors"].append(f"Date parsing error: {e!s}")
                    else:
                        result["errors"].append("Revenue row not found in DataFrame")
                else:
                    result["errors"].append(f"Income statement not a DataFrame: {type(income_stmt)}")
            else:
                result["errors"].append("Income statement is None")

        except Exception as e:
            result["errors"].append(f"Manual extraction error: {e!s}")
            print(f"Error: {e}")

        # METHOD 3: Test getter methods (single period only)
        print("\n--- METHOD 3: Getter Methods (Latest Period Only) ---")
        try:
            revenue = tenk.financials.get_revenue()
            if revenue:
                print(f"get_revenue(): ${revenue:,.0f}")
                # Getter methods only return single period, not useful for time series
            else:
                result["errors"].append("get_revenue() returned None")
        except Exception as e:
            result["errors"].append(f"get_revenue() error: {e!s}")
            print(f"Error: {e}")

    except Exception as e:
        result["errors"].append(f"Company-level error: {e!s}")
        print(f"ERROR: {e}")

    return result


def print_summary(results: list[dict]):
    """Print summary of all test results"""
    print("\n" + "=" * 80)
    print("SUMMARY: Time Series Data Extraction Test")
    print("=" * 80)

    total = len(results)
    successful = sum(1 for r in results if r["success"])

    print(f"\nSuccess Rate: {successful}/{total} ({successful / total * 100:.1f}%)")

    # Group by sector
    print(f"\n{'Sector':<15} {'Ticker':<8} {'Success':<10} {'Years':<8} {'CAGR 10Y':<12} {'Method'}")
    print("-" * 80)

    for sector, tickers in TEST_COMPANIES.items():
        for ticker in tickers:
            result = next(r for r in results if r["ticker"] == ticker)
            success_str = "✅" if result["success"] else "❌"
            years = result["years_available"]
            cagr = f"{result['cagr_10y']:.2f}%" if result["cagr_10y"] else "N/A"
            method = result["method_used"] or "N/A"

            print(f"{sector:<15} {ticker:<8} {success_str:<10} {years:<8} {cagr:<12} {method}")

    # XBRL tag consistency
    print(f"\n{'=' * 80}")
    print("XBRL Tag Consistency")
    print("=" * 80)

    revenue_tags = {}
    for result in results:
        if result["revenue_tag"]:
            tag = result["revenue_tag"]
            if tag not in revenue_tags:
                revenue_tags[tag] = []
            revenue_tags[tag].append(result["ticker"])

    print(f"\nUnique revenue tags found: {len(revenue_tags)}")
    for tag, tickers in revenue_tags.items():
        print(f"  {tag}: {', '.join(tickers)}")

    # Historical data availability
    print(f"\n{'=' * 80}")
    print("Historical Data Availability")
    print("=" * 80)

    years_dist = {}
    for result in results:
        years = result["years_available"]
        if years not in years_dist:
            years_dist[years] = []
        years_dist[years].append(result["ticker"])

    for years in sorted(years_dist.keys(), reverse=True):
        tickers = years_dist[years]
        print(f"  {years} years: {', '.join(tickers)}")

    # Error analysis
    print(f"\n{'=' * 80}")
    print("Common Errors")
    print("=" * 80)

    all_errors = []
    for result in results:
        all_errors.extend(result["errors"])

    if all_errors:
        error_counts = {}
        for error in all_errors:
            # Simplify error message
            error_key = error.split(":")[0]
            error_counts[error_key] = error_counts.get(error_key, 0) + 1

        for error, count in sorted(error_counts.items(), key=lambda x: -x[1]):
            print(f"  {error}: {count} occurrences")
    else:
        print("  No errors!")


def main():
    """Run all tests and generate report"""
    print("=" * 80)
    print("Time Series Data Extraction Test for CAGR Calculations")
    print("=" * 80)
    print(f"Testing {len(FLAT_TICKERS)} companies across {len(TEST_COMPANIES)} sectors")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = []

    for ticker in FLAT_TICKERS:
        result = test_company_time_series(ticker)
        results.append(result)

    # Print summary
    print_summary(results)

    # Save detailed results to JSON
    output_file = "research/time_series_test_results.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Recommendations
    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    total = len(results)

    if successful >= total * 0.8:
        print("✅ PASS: 80%+ success rate achieved")
        print("\nRecommended approach:")

        # Count methods used
        methods = [r["method_used"] for r in results if r["method_used"]]
        if methods:
            from collections import Counter

            method_counts = Counter(methods)
            most_common = method_counts.most_common(1)[0][0]
            print(f"  Primary: {most_common} (used by {method_counts[most_common]} companies)")

        # Check for consistent tags
        revenue_tags = [r["revenue_tag"] for r in results if r["revenue_tag"]]
        unique_tags = set(revenue_tags)
        if len(unique_tags) == 1:
            print(f"  Revenue tag: {list(unique_tags)[0]} (100% consistent)")
        else:
            print(f"  Revenue tags: {len(unique_tags)} variants (need lightweight mapper)")
    else:
        print(f"❌ FAIL: {successful / total * 100:.1f}% success rate (need 80%+)")
        print("\nNext steps:")
        print("  1. Investigate failures")
        print("  2. Test alternative approaches")
        print("  3. Consider fallback to query multiple 10-K filings")


if __name__ == "__main__":
    main()
