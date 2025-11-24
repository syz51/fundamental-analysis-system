"""
Test Multi-Filing Approach for 10-Year Revenue CAGR

Research Questions:
1. How many 10-K filings needed to get 10 years of data?
2. How long does it take to query multiple filings?
3. Is it feasible for screening 500 companies?
4. How much do 3Y vs 10Y CAGR values differ?

Strategy:
- Each 10-K has 3 years of comparative data
- Query 4 filings to get ~10-12 years
- Extract oldest year from each to avoid overlap
- Performance: 4 filings × 500 companies = 2000 API calls
"""

import time
from datetime import datetime

import pandas as pd
from edgar import Company, set_identity

set_identity("YourName your.email@example.com")

# Test on 5 companies for speed
TEST_COMPANIES = ["AAPL", "MSFT", "JPM", "WMT", "SNOW"]


def extract_date_columns(df: pd.DataFrame) -> list[str]:
    """Extract and sort date columns from DataFrame"""
    metadata_cols = ["concept", "label", "level", "abstract", "dimension", "balance", "weight", "preferred_sign"]
    potential_date_cols = [col for col in df.columns if col not in metadata_cols]

    date_cols = []
    for col in potential_date_cols:
        try:
            pd.to_datetime(col)
            date_cols.append(col)
        except:
            pass

    return sorted(date_cols)


def extract_revenue_row(df: pd.DataFrame, date_cols: list[str]):
    """Extract revenue row, filtering out NaN headers"""
    revenue_matches = df[df["label"].str.contains("revenue", case=False, na=False)]

    if revenue_matches.empty:
        return None

    # Filter out rows with all NaN values
    valid_matches = revenue_matches[revenue_matches[date_cols].notna().any(axis=1)]

    if valid_matches.empty:
        return None

    # Prefer "total" or shorter labels
    total_matches = valid_matches[valid_matches["label"].str.contains("total", case=False, na=False)]
    if not total_matches.empty:
        return total_matches.iloc[0]

    # Otherwise take shortest label
    valid_matches = valid_matches.copy()
    valid_matches["label_len"] = valid_matches["label"].str.len()
    return valid_matches.sort_values("label_len").iloc[0]


def calculate_cagr(start_value: float, end_value: float, years: float) -> float:
    """Calculate CAGR"""
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    return ((end_value / start_value) ** (1 / years) - 1) * 100


def extract_revenue_history_single_filing(ticker: str) -> tuple[dict, float]:
    """Extract 3Y revenue from single filing (baseline)"""
    start_time = time.time()

    company = Company(ticker)
    filing = company.get_filings(form="10-K").latest(1)
    df = filing.obj().income_statement.to_dataframe()

    date_cols = extract_date_columns(df)
    revenue_row = extract_revenue_row(df, date_cols)

    revenue_history = {}
    if revenue_row is not None:
        for col in date_cols:
            if pd.notna(revenue_row[col]):
                revenue_history[col] = float(revenue_row[col])

    elapsed = time.time() - start_time
    return revenue_history, elapsed


def extract_revenue_history_multi_filing(ticker: str, num_filings: int = 4) -> tuple[dict, float, int]:
    """
    Extract 10Y+ revenue from multiple filings

    Returns: (revenue_history, elapsed_time, filings_fetched)
    """
    start_time = time.time()

    company = Company(ticker)
    filings = company.get_filings(form="10-K").latest(num_filings)

    revenue_history = {}
    filings_fetched = 0

    for filing in filings:
        filings_fetched += 1

        try:
            df = filing.obj().income_statement.to_dataframe()
            date_cols = extract_date_columns(df)
            revenue_row = extract_revenue_row(df, date_cols)

            if revenue_row is not None:
                # Extract all years from this filing
                for col in date_cols:
                    if pd.notna(revenue_row[col]):
                        # Only add if we don't already have this year
                        if col not in revenue_history:
                            revenue_history[col] = float(revenue_row[col])
        except Exception as e:
            print(f"  Warning: Failed to process filing {filing.filing_date}: {e}")
            continue

    elapsed = time.time() - start_time
    return revenue_history, elapsed, filings_fetched


def test_company(ticker: str) -> dict:
    """Test both single and multi-filing approaches"""
    print(f"\n{'=' * 70}")
    print(f"Testing: {ticker}")
    print(f"{'=' * 70}")

    result = {"ticker": ticker, "single_filing": {}, "multi_filing": {}, "comparison": {}}

    # Test single filing (3Y)
    print("\n--- Single Filing (3Y baseline) ---")
    try:
        revenue_3y, time_3y = extract_revenue_history_single_filing(ticker)

        if revenue_3y:
            years_3y = sorted(revenue_3y.keys())
            oldest = years_3y[0]
            newest = years_3y[-1]

            oldest_date = pd.to_datetime(oldest)
            newest_date = pd.to_datetime(newest)
            duration = (newest_date - oldest_date).days / 365.25

            cagr_3y = calculate_cagr(revenue_3y[oldest], revenue_3y[newest], duration)

            result["single_filing"] = {
                "years_available": len(revenue_3y),
                "date_range": f"{oldest} to {newest}",
                "duration_years": round(duration, 1),
                "cagr": round(cagr_3y, 2) if cagr_3y else None,
                "time_elapsed": round(time_3y, 2),
                "oldest_revenue": revenue_3y[oldest],
                "newest_revenue": revenue_3y[newest],
            }

            print(f"Years: {len(revenue_3y)}")
            print(f"Range: {oldest} to {newest} ({duration:.1f} years)")
            print(f"CAGR: {cagr_3y:.2f}%")
            print(f"Time: {time_3y:.2f}s")
        else:
            print("Failed to extract revenue")
            result["single_filing"]["error"] = "No revenue data"

    except Exception as e:
        print(f"Error: {e}")
        result["single_filing"]["error"] = str(e)

    # Test multi-filing (10Y+)
    print("\n--- Multi-Filing (10Y+ target) ---")
    try:
        revenue_10y, time_10y, filings_count = extract_revenue_history_multi_filing(ticker, num_filings=4)

        if revenue_10y:
            years_10y = sorted(revenue_10y.keys())
            oldest = years_10y[0]
            newest = years_10y[-1]

            oldest_date = pd.to_datetime(oldest)
            newest_date = pd.to_datetime(newest)
            duration = (newest_date - oldest_date).days / 365.25

            cagr_10y = calculate_cagr(revenue_10y[oldest], revenue_10y[newest], duration)

            result["multi_filing"] = {
                "years_available": len(revenue_10y),
                "date_range": f"{oldest} to {newest}",
                "duration_years": round(duration, 1),
                "cagr": round(cagr_10y, 2) if cagr_10y else None,
                "time_elapsed": round(time_10y, 2),
                "filings_fetched": filings_count,
                "oldest_revenue": revenue_10y[oldest],
                "newest_revenue": revenue_10y[newest],
            }

            print(f"Filings fetched: {filings_count}")
            print(f"Years: {len(revenue_10y)}")
            print(f"Range: {oldest} to {newest} ({duration:.1f} years)")
            print(f"CAGR: {cagr_10y:.2f}%")
            print(f"Time: {time_10y:.2f}s")

            # Print full history
            print("\nFull revenue history:")
            for year in sorted(revenue_10y.keys()):
                print(f"  {year}: ${revenue_10y[year]:,.0f}")

        else:
            print("Failed to extract revenue")
            result["multi_filing"]["error"] = "No revenue data"

    except Exception as e:
        print(f"Error: {e}")
        result["multi_filing"]["error"] = str(e)

    # Comparison
    if "cagr" in result["single_filing"] and "cagr" in result["multi_filing"]:
        cagr_3y = result["single_filing"]["cagr"]
        cagr_10y = result["multi_filing"]["cagr"]

        result["comparison"] = {
            "cagr_difference": round(abs(cagr_10y - cagr_3y), 2),
            "time_overhead": round(result["multi_filing"]["time_elapsed"] - result["single_filing"]["time_elapsed"], 2),
            "api_calls_ratio": f"1 → {filings_count}",
        }

        print("\n--- Comparison ---")
        print(f"3Y CAGR: {cagr_3y:.2f}% | 10Y CAGR: {cagr_10y:.2f}%")
        print(f"Difference: {abs(cagr_10y - cagr_3y):.2f} percentage points")
        print(f"Time overhead: +{result['comparison']['time_overhead']:.2f}s ({filings_count}x API calls)")

    return result


def main():
    """Run tests and generate summary"""
    print("=" * 70)
    print("Multi-Filing Approach Test for 10-Year Revenue CAGR")
    print("=" * 70)
    print(f"Testing {len(TEST_COMPANIES)} companies")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = []
    total_start = time.time()

    for ticker in TEST_COMPANIES:
        result = test_company(ticker)
        results.append(result)

    total_elapsed = time.time() - total_start

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)

    print(f"\n{'Ticker':<8} {'3Y CAGR':<10} {'10Y CAGR':<10} {'Diff':<8} {'Time (s)':<10} {'Years'}")
    print("-" * 70)

    total_time_single = 0
    total_time_multi = 0

    for r in results:
        ticker = r["ticker"]
        cagr_3y = r["single_filing"].get("cagr", "N/A")
        cagr_10y = r["multi_filing"].get("cagr", "N/A")
        diff = r["comparison"].get("cagr_difference", "N/A")
        time_multi = r["multi_filing"].get("time_elapsed", 0)
        years = r["multi_filing"].get("years_available", "N/A")

        total_time_single += r["single_filing"].get("time_elapsed", 0)
        total_time_multi += time_multi

        cagr_3y_str = f"{cagr_3y:.2f}%" if isinstance(cagr_3y, (int, float)) else str(cagr_3y)
        cagr_10y_str = f"{cagr_10y:.2f}%" if isinstance(cagr_10y, (int, float)) else str(cagr_10y)
        diff_str = f"{diff:.2f}pp" if isinstance(diff, (int, float)) else str(diff)

        print(f"{ticker:<8} {cagr_3y_str:<10} {cagr_10y_str:<10} {diff_str:<8} {time_multi:<10.2f} {years}")

    # Extrapolation to 500 companies
    print(f"\n{'=' * 70}")
    print("EXTRAPOLATION TO S&P 500 SCREENING")
    print("=" * 70)

    avg_time_single = total_time_single / len(TEST_COMPANIES)
    avg_time_multi = total_time_multi / len(TEST_COMPANIES)

    print("\nAverage time per company:")
    print(f"  Single filing (3Y): {avg_time_single:.2f}s")
    print(f"  Multi-filing (10Y): {avg_time_multi:.2f}s")

    print("\nFor 500 companies:")
    print(f"  Single filing: {avg_time_single * 500:.0f}s ({avg_time_single * 500 / 60:.1f} min)")
    print(f"  Multi-filing: {avg_time_multi * 500:.0f}s ({avg_time_multi * 500 / 60:.1f} min)")

    print("\nAPI Calls:")
    print("  Single filing: 500 calls")
    print("  Multi-filing: ~2000 calls (4 per company)")

    # Rate limit consideration
    print("\nSEC Rate Limit (10 req/sec):")
    print(f"  Single filing: {500 / 10:.0f}s ({500 / 10 / 60:.1f} min) minimum")
    print(f"  Multi-filing: {2000 / 10:.0f}s ({2000 / 10 / 60:.1f} min) minimum")

    # Recommendation
    print(f"\n{'=' * 70}")
    print("RECOMMENDATION")
    print("=" * 70)

    avg_diff = sum(
        r["comparison"].get("cagr_difference", 0) for r in results if "cagr_difference" in r["comparison"]
    ) / len([r for r in results if "cagr_difference" in r["comparison"]])

    print(f"\nAverage CAGR difference (3Y vs 10Y): {avg_diff:.2f} percentage points")

    if avg_time_multi * 500 / 60 <= 10:  # 10 minutes threshold
        print("\n✅ FEASIBLE for screening:")
        print(f"   - Total time: ~{avg_time_multi * 500 / 60:.1f} min for 500 companies")
        print(f"   - Rate limit: {2000 / 10 / 60:.1f} min minimum")
        print("   - Provides true 10Y CAGR for all companies")
    else:
        print("\n⚠️ CONSIDER TRADEOFFS:")
        print(f"   - Multi-filing adds {avg_time_multi * 500 / 60 - avg_time_single * 500 / 60:.1f} min")
        print(f"   - 3Y CAGR differs by only {avg_diff:.2f}pp on average")
        print("   - Option: Use 3Y for screening, 10Y for finalists")

    print(f"\nTotal test time: {total_elapsed:.2f}s")


if __name__ == "__main__":
    main()
