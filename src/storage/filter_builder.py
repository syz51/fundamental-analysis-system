"""Elasticsearch filter construction utilities."""

from typing import Any


class SearchFilterBuilder:
    """Constructs Elasticsearch filter clauses for search queries."""

    def build(
        self,
        ticker: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Constructs Elasticsearch filter clauses.

        Args:
            ticker: Optional stock ticker to filter by
            start_date: Optional start date (ISO format) for date range filtering
            end_date: Optional end date (ISO format) for date range filtering
            filters: Optional additional filters as key-value pairs

        Returns:
            List of Elasticsearch filter clause dictionaries
        """
        es_filters = []

        if ticker:
            es_filters.append({"term": {"ticker": ticker}})

        if start_date or end_date:
            range_clause: dict[str, str] = {}
            if start_date:
                range_clause["gte"] = start_date
            if end_date:
                range_clause["lte"] = end_date
            range_filter: dict[str, Any] = {"range": {"date": range_clause}}
            es_filters.append(range_filter)

        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    filter_dict: dict[str, Any] = {"terms": {key: value}}
                    es_filters.append(filter_dict)
                else:
                    filter_dict_term: dict[str, Any] = {"term": {key: value}}
                    es_filters.append(filter_dict_term)

        return es_filters
