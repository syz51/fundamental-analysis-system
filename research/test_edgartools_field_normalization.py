"""
Research Script: Test EdgarTools Field Normalization

Purpose: Determine if EdgarTools normalizes US-GAAP XBRL tags to standard field names.
This will decide if the FieldMapper module (200+ lines) is needed.

Test Plan:
1. Query 10 random S&P 500 companies
2. Check if financials.income.revenue works directly
3. Inspect actual field names returned
4. Document findings

Expected Results:
- If YES (normalized): Field mapper is redundant
- If NO (raw tags): Field mapper is critical
"""

import logging
import sys
from typing import Any

from edgar import Company, set_identity

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# Test companies (diverse selection from S&P 500)
TEST_TICKERS = [
    "AAPL",  # Technology - Apple
    "MSFT",  # Technology - Microsoft
    "JPM",  # Financials - JPMorgan Chase
    "JNJ",  # Healthcare - Johnson & Johnson
    "XOM",  # Energy - Exxon Mobil
    "WMT",  # Consumer - Walmart
    "PG",  # Consumer Staples - Procter & Gamble
    "UNH",  # Healthcare - UnitedHealth
    "HD",  # Retail - Home Depot
    "V",  # Financials - Visa
]


def test_field_normalization(ticker: str) -> dict[str, Any]:
    """Test field normalization for a single company.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dict with test results
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Testing: {ticker}")
    logger.info(f"{'=' * 60}")

    result = {
        "ticker": ticker,
        "success": False,
        "has_financials": False,
        "normalized_access_works": False,
        "available_attributes": [],
        "income_statement_fields": [],
        "balance_sheet_fields": [],
        "sample_values": {},
        "error": None,
    }

    try:
        # Query company
        company = Company(ticker)
        logger.info(f"✓ Company object created: {company.name if hasattr(company, 'name') else 'N/A'}")

        # Get financials
        financials = company.get_financials()

        if not financials:
            logger.warning(f"✗ No financials available for {ticker}")
            result["error"] = "No financials available"
            return result

        result["has_financials"] = True
        logger.info("✓ Financials retrieved")

        # Check what attributes are available
        result["available_attributes"] = [attr for attr in dir(financials) if not attr.startswith("_")]
        logger.info(f"Available financials attributes: {result['available_attributes']}")

        # Test normalized field access (income statement)
        if hasattr(financials, "income"):
            income = financials.income
            logger.info("\n✓ Income statement accessible via .income")

            # List available fields
            if hasattr(income, "columns") or hasattr(income, "index"):
                # It's a DataFrame
                if hasattr(income, "columns"):
                    result["income_statement_fields"] = income.columns.tolist()
                    logger.info(f"Income statement columns: {result['income_statement_fields'][:10]}...")
                elif hasattr(income, "index"):
                    result["income_statement_fields"] = income.index.tolist()
                    logger.info(f"Income statement index: {result['income_statement_fields'][:10]}...")

            # Test specific field access
            test_fields = ["revenue", "Revenues", "net_income", "NetIncomeLoss", "operating_income"]

            for field in test_fields:
                try:
                    if hasattr(income, field):
                        value = getattr(income, field)
                        logger.info(f"  ✓ .income.{field} accessible")
                        result["sample_values"][f"income.{field}"] = str(
                            value.iloc[-1] if hasattr(value, "iloc") else value
                        )[:100]
                        result["normalized_access_works"] = True
                    # Try as DataFrame column/index
                    elif hasattr(income, "loc"):
                        try:
                            value = income.loc[field]
                            logger.info(f"  ✓ income.loc['{field}'] accessible")
                            result["sample_values"][f"income.loc[{field}]"] = str(
                                value.iloc[-1] if hasattr(value, "iloc") else value
                            )[:100]
                            result["normalized_access_works"] = True
                        except KeyError:
                            logger.info(f"  ✗ income.loc['{field}'] not found")
                    elif hasattr(income, "__getitem__"):
                        try:
                            value = income[field]
                            logger.info(f"  ✓ income['{field}'] accessible")
                            result["sample_values"][f"income[{field}]"] = str(
                                value.iloc[-1] if hasattr(value, "iloc") else value
                            )[:100]
                            result["normalized_access_works"] = True
                        except (KeyError, IndexError):
                            logger.info(f"  ✗ income['{field}'] not found")

                except Exception as e:
                    logger.info(f"  ✗ .income.{field} failed: {e}")

        # Test balance sheet access
        if hasattr(financials, "balance"):
            balance = financials.balance
            logger.info("\n✓ Balance sheet accessible via .balance")

            if hasattr(balance, "columns"):
                result["balance_sheet_fields"] = balance.columns.tolist()
                logger.info(f"Balance sheet columns: {result['balance_sheet_fields'][:10]}...")
            elif hasattr(balance, "index"):
                result["balance_sheet_fields"] = balance.index.tolist()
                logger.info(f"Balance sheet index: {result['balance_sheet_fields'][:10]}...")

            # Test specific field access
            test_fields = ["total_assets", "Assets", "stockholders_equity", "StockholdersEquity"]

            for field in test_fields:
                try:
                    if hasattr(balance, field):
                        value = getattr(balance, field)
                        logger.info(f"  ✓ .balance.{field} accessible")
                        result["sample_values"][f"balance.{field}"] = str(
                            value.iloc[-1] if hasattr(value, "iloc") else value
                        )[:100]
                    elif hasattr(balance, "loc"):
                        try:
                            value = balance.loc[field]
                            logger.info(f"  ✓ balance.loc['{field}'] accessible")
                            result["sample_values"][f"balance.loc[{field}]"] = str(
                                value.iloc[-1] if hasattr(value, "iloc") else value
                            )[:100]
                        except KeyError:
                            logger.info(f"  ✗ balance.loc['{field}'] not found")
                    elif hasattr(balance, "__getitem__"):
                        try:
                            value = balance[field]
                            logger.info(f"  ✓ balance['{field}'] accessible")
                            result["sample_values"][f"balance[{field}]"] = str(
                                value.iloc[-1] if hasattr(value, "iloc") else value
                            )[:100]
                        except (KeyError, IndexError):
                            logger.info(f"  ✗ balance['{field}'] not found")

                except Exception as e:
                    logger.info(f"  ✗ .balance.{field} failed: {e}")

        result["success"] = True
        logger.info(f"\n✓ Test completed successfully for {ticker}")

    except Exception as e:
        logger.error(f"✗ Error testing {ticker}: {e}")
        result["error"] = str(e)

    return result


def main():
    """Run field normalization tests."""
    logger.info("=" * 60)
    logger.info("EdgarTools Field Normalization Research")
    logger.info("=" * 60)

    # Set up EdgarTools (required by SEC)
    set_identity("research@example.com")  # Replace with your email

    logger.info("\nConfiguration:")
    logger.info("  Email: research@example.com")
    logger.info(f"  Test Companies: {len(TEST_TICKERS)}")

    # Run tests
    results = []
    for ticker in TEST_TICKERS:
        result = test_field_normalization(ticker)
        results.append(result)

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    successful = [r for r in results if r["success"]]
    has_financials = [r for r in results if r["has_financials"]]
    normalized_works = [r for r in results if r["normalized_access_works"]]

    logger.info(f"\nTotal Tests: {len(results)}")
    logger.info(f"Successful: {len(successful)} ({len(successful) / len(results) * 100:.1f}%)")
    logger.info(f"Has Financials: {len(has_financials)} ({len(has_financials) / len(results) * 100:.1f}%)")
    logger.info(f"Normalized Access Works: {len(normalized_works)} ({len(normalized_works) / len(results) * 100:.1f}%)")

    # Detailed findings
    logger.info("\n" + "=" * 60)
    logger.info("DETAILED FINDINGS")
    logger.info("=" * 60)

    for result in results:
        logger.info(f"\n{result['ticker']}:")
        logger.info(f"  Success: {result['success']}")
        logger.info(f"  Has Financials: {result['has_financials']}")
        logger.info(f"  Normalized Access: {result['normalized_access_works']}")

        if result["income_statement_fields"]:
            logger.info(f"  Income Statement Fields (first 5): {result['income_statement_fields'][:5]}")

        if result["balance_sheet_fields"]:
            logger.info(f"  Balance Sheet Fields (first 5): {result['balance_sheet_fields'][:5]}")

        if result["sample_values"]:
            logger.info("  Sample Values:")
            for key, value in list(result["sample_values"].items())[:3]:
                logger.info(f"    {key}: {value}")

        if result["error"]:
            logger.info(f"  Error: {result['error']}")

    # Conclusion
    logger.info("\n" + "=" * 60)
    logger.info("CONCLUSION")
    logger.info("=" * 60)

    if len(normalized_works) >= len(has_financials) * 0.8:  # 80% threshold
        logger.info("\n✓ RESULT: EdgarTools appears to support normalized field access")
        logger.info("  Recommendation: Field mapper may be redundant")
        logger.info("  Action: Review actual field names and decide if mapper needed for edge cases")
    else:
        logger.info("\n✗ RESULT: EdgarTools does NOT reliably support normalized field access")
        logger.info("  Recommendation: Field mapper is CRITICAL")
        logger.info("  Action: Implement full field mapper with comprehensive tag mappings")

    logger.info("\nNext Steps:")
    logger.info("  1. Review detailed findings above")
    logger.info("  2. Inspect actual field names used by EdgarTools")
    logger.info("  3. Decide on field mapper implementation strategy")
    logger.info("  4. Update implementation plan accordingly")


if __name__ == "__main__":
    main()
