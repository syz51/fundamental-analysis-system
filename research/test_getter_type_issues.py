"""
Investigate type issues with EdgarTools getter methods

Some companies return strings instead of floats, causing arithmetic errors.
"""

from edgar import Company, set_identity

set_identity("Research research@example.com")


def test_getter_types(ticker: str):
    """Test what types the getter methods return"""
    print(f"\n{'=' * 80}")
    print(f"{ticker} - Investigating Getter Method Return Types")
    print(f"{'=' * 80}")

    try:
        company = Company(ticker)
        financials = company.get_financials()

        # Test each getter method
        getters = [
            "get_revenue",
            "get_net_income",
            "get_total_assets",
            "get_stockholders_equity",
            "get_operating_cash_flow",
            "get_free_cash_flow",
            "get_current_assets",
            "get_current_liabilities",
        ]

        results = {}
        for getter_name in getters:
            try:
                value = getattr(financials, getter_name)()
                value_type = type(value).__name__
                print(f"✅ {getter_name}(): {value} (type: {value_type})")

                # Try to convert to float if it's a string
                if isinstance(value, str):
                    try:
                        # Remove commas and convert
                        cleaned = value.replace(",", "")
                        float_value = float(cleaned)
                        print(f"   → Convertible to float: {float_value}")
                        results[getter_name] = ("str_convertible", value, float_value)
                    except ValueError:
                        print("   → NOT convertible to float")
                        results[getter_name] = ("str_not_convertible", value, None)
                elif isinstance(value, (int, float)):
                    results[getter_name] = ("numeric", value, float(value))
                else:
                    results[getter_name] = ("other", value, None)

            except AttributeError:
                print(f"❌ {getter_name}(): Method does not exist")
                results[getter_name] = ("missing", None, None)
            except Exception as e:
                print(f"❌ {getter_name}(): Error - {e}")
                results[getter_name] = ("error", str(e), None)

        return results

    except Exception as e:
        print(f"❌ Failed to get financials for {ticker}: {e}")
        return {}


if __name__ == "__main__":
    test_tickers = ["AAPL", "JPM", "JNJ", "XOM", "WMT"]
    all_results = {}

    for ticker in test_tickers:
        results = test_getter_types(ticker)
        all_results[ticker] = results

    # Summary
    print(f"\n\n{'=' * 80}")
    print("SUMMARY: Type Analysis Across Companies")
    print(f"{'=' * 80}")

    # Check consistency across getter methods
    for ticker in test_tickers:
        print(f"\n{ticker}:")
        if ticker in all_results:
            type_counts = {}
            for getter, (type_cat, _, _) in all_results[ticker].items():
                type_counts[type_cat] = type_counts.get(type_cat, 0) + 1

            print(f"  Type distribution: {type_counts}")

            # Check if all are convertible
            all_convertible = all(cat in ["numeric", "str_convertible"] for cat, _, _ in all_results[ticker].values())
            print(f"  All convertible to float: {all_convertible}")

    # Recommendation
    print(f"\n\n{'=' * 80}")
    print("RECOMMENDATION")
    print(f"{'=' * 80}")
    print("\nIf all getter methods return either:")
    print("  1. Numeric values (int/float)")
    print("  2. String values convertible to float")
    print("\nThen we can:")
    print("  ✅ Use getter methods with type normalization wrapper")
    print("  ✅ Avoid complex FieldMapper")
    print("\nExample wrapper:")
    print("""
def safe_float(value):
    '''Convert EdgarTools getter result to float'''
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, str):
        return float(value.replace(',', ''))
    else:
        raise TypeError(f"Cannot convert {type(value)} to float")

# Usage
revenue = safe_float(financials.get_revenue())
    """)
