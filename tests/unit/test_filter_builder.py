"""Tests for SearchFilterBuilder covering all parameter combinations."""

import pytest

from storage.filter_builder import SearchFilterBuilder

# Test constants
DEFAULT_LIMIT = 3

pytestmark = pytest.mark.unit


class TestBuildFilters:
    """Tests for SearchFilterBuilder.build() method."""

    def test_build_filters_empty(self) -> None:
        """No filters returns empty list."""
        builder = SearchFilterBuilder()
        filters = builder.build(ticker=None, start_date=None, end_date=None, filters=None)

        assert filters == []

    def test_build_filters_ticker_only(self) -> None:
        """Ticker filter creates term query."""
        builder = SearchFilterBuilder()
        filters = builder.build(ticker="AAPL", start_date=None, end_date=None, filters=None)

        assert len(filters) == 1
        assert filters[0] == {"term": {"ticker": "AAPL"}}

    def test_build_filters_date_range_start_only(self) -> None:
        """Start date only creates range query with gte."""
        builder = SearchFilterBuilder()
        filters = builder.build(ticker=None, start_date="2024-01-01", end_date=None, filters=None)

        assert len(filters) == 1
        assert filters[0] == {"range": {"date": {"gte": "2024-01-01"}}}

    def test_build_filters_date_range_end_only(self) -> None:
        """End date only creates range query with lte."""
        builder = SearchFilterBuilder()
        filters = builder.build(ticker=None, start_date=None, end_date="2024-12-31", filters=None)

        assert len(filters) == 1
        assert filters[0] == {"range": {"date": {"lte": "2024-12-31"}}}

    def test_build_filters_date_range_both(self) -> None:
        """Both start and end date creates range query with gte and lte."""
        builder = SearchFilterBuilder()
        filters = builder.build(
            ticker=None,
            start_date="2024-01-01",
            end_date="2024-12-31",
            filters=None,
        )

        assert len(filters) == 1
        assert filters[0] == {"range": {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}}

    def test_build_filters_custom_term_single_value(self) -> None:
        """Custom filter with single value creates term query."""
        builder = SearchFilterBuilder()
        filters = builder.build(
            ticker=None,
            start_date=None,
            end_date=None,
            filters={"sector": "Technology"},
        )

        assert len(filters) == 1
        assert filters[0] == {"term": {"sector": "Technology"}}

    def test_build_filters_custom_terms_list_value(self) -> None:
        """Custom filter with list value creates terms query."""
        builder = SearchFilterBuilder()
        filters = builder.build(
            ticker=None,
            start_date=None,
            end_date=None,
            filters={"sector": ["Technology", "Finance"]},
        )

        assert len(filters) == 1
        assert filters[0] == {"terms": {"sector": ["Technology", "Finance"]}}

    def test_build_filters_multiple_custom_filters(self) -> None:
        """Multiple custom filters all added."""
        builder = SearchFilterBuilder()
        filters = builder.build(
            ticker=None,
            start_date=None,
            end_date=None,
            filters={
                "sector": "Technology",
                "industry": ["Software", "Hardware"],
                "doc_type": "10-K",
            },
        )

        assert len(filters) == DEFAULT_LIMIT
        # Check all expected filters present (order may vary)
        filter_set = {str(f) for f in filters}
        assert str({"term": {"sector": "Technology"}}) in filter_set
        assert str({"terms": {"industry": ["Software", "Hardware"]}}) in filter_set
        assert str({"term": {"doc_type": "10-K"}}) in filter_set

    def test_build_filters_combined_all_types(self) -> None:
        """Ticker + date range + custom filters all combined."""
        builder = SearchFilterBuilder()
        filters = builder.build(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-12-31",
            filters={"sector": "Technology"},
        )

        assert len(filters) == DEFAULT_LIMIT
        # Verify each filter type present
        assert {"term": {"ticker": "AAPL"}} in filters
        assert {"range": {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}} in filters
        assert {"term": {"sector": "Technology"}} in filters


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
