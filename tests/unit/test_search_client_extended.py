"""Extended unit tests for SearchClient covering uncovered paths."""

from unittest.mock import AsyncMock, patch

import pytest
from src.storage.search_tool import SearchClient, SearchConfig

# Test constants
EMBEDDING_DIMS = 1536
MOCK_EMBEDDING_VALUE = 0.001
DEFAULT_LIMIT = 3
KNN_K_VALUE = 10
NUM_CANDIDATES = 100
RRF_K = 60
OVERLAP_COUNT = 2
RRF_TOLERANCE = 0.001


class TestSearchClientClose:
    """Tests for SearchClient.close() method."""

    @pytest.mark.asyncio
    async def test_close_calls_client_close(self):
        """close() should call the underlying Elasticsearch client close."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            client = SearchClient("http://localhost:9200")
            await client.close()

            # Verify close was called
            mock_es_instance.close.assert_called_once()


class TestGenerateEmbedding:
    """Tests for _generate_embedding method."""

    @pytest.mark.asyncio
    async def test_generate_embedding_mock_mode(self):
        """In mock mode, returns deterministic 1536-dim vector."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200", embedding_model_mock=True)
            vector = await client._generate_embedding("test query")

            assert isinstance(vector, list)
            assert len(vector) == EMBEDDING_DIMS
            assert all(v == MOCK_EMBEDDING_VALUE for v in vector)

    @pytest.mark.asyncio
    async def test_generate_embedding_real_mode_not_implemented(self):
        """When mock=False, raises NotImplementedError."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200", embedding_model_mock=False)

            with pytest.raises(NotImplementedError, match="Real embedding model not configured"):
                await client._generate_embedding("test query")


class TestBuildFilters:
    """Tests for _build_filters method covering all parameter combinations."""

    def test_build_filters_empty(self):
        """No filters returns empty list."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(ticker=None, start_date=None, end_date=None, filters=None)

            assert filters == []

    def test_build_filters_ticker_only(self):
        """Ticker filter creates term query."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(ticker="AAPL", start_date=None, end_date=None, filters=None)

            assert len(filters) == 1
            assert filters[0] == {"term": {"ticker": "AAPL"}}

    def test_build_filters_date_range_start_only(self):
        """Start date only creates range query with gte."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(ticker=None, start_date="2024-01-01", end_date=None, filters=None)

            assert len(filters) == 1
            assert filters[0] == {"range": {"date": {"gte": "2024-01-01"}}}

    def test_build_filters_date_range_end_only(self):
        """End date only creates range query with lte."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(ticker=None, start_date=None, end_date="2024-12-31", filters=None)

            assert len(filters) == 1
            assert filters[0] == {"range": {"date": {"lte": "2024-12-31"}}}

    def test_build_filters_date_range_both(self):
        """Both start and end date creates range query with gte and lte."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(
                ticker=None,
                start_date="2024-01-01",
                end_date="2024-12-31",
                filters=None,
            )

            assert len(filters) == 1
            assert filters[0] == {"range": {"date": {"gte": "2024-01-01", "lte": "2024-12-31"}}}

    def test_build_filters_custom_term_single_value(self):
        """Custom filter with single value creates term query."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(
                ticker=None,
                start_date=None,
                end_date=None,
                filters={"sector": "Technology"},
            )

            assert len(filters) == 1
            assert filters[0] == {"term": {"sector": "Technology"}}

    def test_build_filters_custom_terms_list_value(self):
        """Custom filter with list value creates terms query."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(
                ticker=None,
                start_date=None,
                end_date=None,
                filters={"sector": ["Technology", "Finance"]},
            )

            assert len(filters) == 1
            assert filters[0] == {"terms": {"sector": ["Technology", "Finance"]}}

    def test_build_filters_multiple_custom_filters(self):
        """Multiple custom filters all added."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(
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

    def test_build_filters_combined_all_types(self):
        """Ticker + date range + custom filters all combined."""
        with patch("src.storage.search_tool.AsyncElasticsearch"):
            client = SearchClient("http://localhost:9200")
            filters = client._build_filters(
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


class TestSemanticSearch:
    """Tests for semantic search query structure (mocked)."""

    @pytest.mark.asyncio
    async def test_semantic_search_query_structure(self):
        """Semantic search builds correct kNN query."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            # Mock search response
            mock_response = {
                "hits": {
                    "hits": [
                        {
                            "_index": "sec_filings",
                            "_id": "doc1",
                            "_score": 0.95,
                            "_source": {
                                "doc_id": "doc1",
                                "text": "Apple revenue growth",
                                "ticker": "AAPL",
                                "date": "2024-01-01",
                            },
                        }
                    ]
                }
            }
            mock_es_instance.search.return_value = mock_response

            client = SearchClient("http://localhost:9200", embedding_model_mock=True)
            config = SearchConfig(limit=KNN_K_VALUE)

            results = await client.search_tool(
                query="revenue growth",
                search_type="semantic",
                config=config,
            )

            # Verify search was called
            mock_es_instance.search.assert_called_once()
            call_kwargs = mock_es_instance.search.call_args[1]

            # Verify kNN query structure
            assert "knn" in call_kwargs
            knn_query = call_kwargs["knn"]
            assert knn_query["field"] == "embedding"
            assert len(knn_query["query_vector"]) == EMBEDDING_DIMS
            assert knn_query["k"] == KNN_K_VALUE
            assert knn_query["num_candidates"] == NUM_CANDIDATES

            # Verify results parsed
            assert len(results) == 1
            assert results[0].doc_id == "doc1"

    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self):
        """Semantic search includes filter clauses in kNN query."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            mock_response = {"hits": {"hits": []}}
            mock_es_instance.search.return_value = mock_response

            client = SearchClient("http://localhost:9200", embedding_model_mock=True)
            config = SearchConfig(
                limit=KNN_K_VALUE,
                ticker="AAPL",
            )

            await client.search_tool(
                query="revenue growth",
                search_type="semantic",
                config=config,
            )

            # Verify filter included in kNN query
            call_kwargs = mock_es_instance.search.call_args[1]
            knn_query = call_kwargs["knn"]
            assert "filter" in knn_query
            assert len(knn_query["filter"]) == 1
            assert knn_query["filter"][0] == {"term": {"ticker": "AAPL"}}


class TestExceptionHandling:
    """Tests for exception handling paths in search."""

    @pytest.mark.asyncio
    async def test_search_unexpected_exception_triggers_circuit_breaker(self):
        """Unexpected exceptions during search trigger circuit breaker."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            # Mock an unexpected exception
            mock_es_instance.search.side_effect = ValueError("Unexpected error")

            client = SearchClient("http://localhost:9200", embedding_model_mock=True)
            config = SearchConfig(limit=KNN_K_VALUE)

            with pytest.raises(ValueError, match="Unexpected error"):
                await client.search_tool(
                    query="test query",
                    search_type="keyword",
                    config=config,
                )

            # Verify circuit breaker recorded failure
            assert client.circuit_breaker.failures == 1


class TestHybridSearch:
    """Tests for hybrid search result merging."""

    @pytest.mark.asyncio
    async def test_hybrid_search_merges_results(self):
        """Hybrid search merges BM25 and kNN results using RRF."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            # Mock BM25 response
            bm25_response = {
                "hits": {
                    "hits": [
                        {
                            "_index": "sec_filings",
                            "_id": "doc1",
                            "_score": 10.0,
                            "_source": {
                                "doc_id": "doc1",
                                "text": "Revenue increased",
                                "ticker": "AAPL",
                            },
                        }
                    ]
                }
            }

            # Mock kNN response
            knn_response = {
                "hits": {
                    "hits": [
                        {
                            "_index": "sec_filings",
                            "_id": "doc2",
                            "_score": 0.9,
                            "_source": {
                                "doc_id": "doc2",
                                "text": "Growth in sales",
                                "ticker": "AAPL",
                            },
                        }
                    ]
                }
            }

            # Mock asyncio.gather to return both responses
            mock_es_instance.search.side_effect = [bm25_response, knn_response]

            client = SearchClient(
                "http://localhost:9200",
                embedding_model_mock=True,
                default_rrf_k=RRF_K,
            )
            config = SearchConfig(limit=KNN_K_VALUE)

            results = await client.search_tool(
                query="revenue growth",
                search_type="hybrid",
                config=config,
            )

            # Verify both searches executed
            assert mock_es_instance.search.call_count == OVERLAP_COUNT

            # Verify RRF merging (should have both docs)
            assert len(results) == OVERLAP_COUNT
            doc_ids = [r.doc_id for r in results]
            assert "doc1" in doc_ids
            assert "doc2" in doc_ids

    @pytest.mark.asyncio
    async def test_hybrid_search_with_overlap(self):
        """Hybrid search correctly merges overlapping docs."""
        with patch("src.storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            # Both searches return same doc
            shared_response = {
                "hits": {
                    "hits": [
                        {
                            "_index": "sec_filings",
                            "_id": "doc1",
                            "_score": 10.0,
                            "_source": {
                                "doc_id": "doc1",
                                "text": "Revenue increased",
                                "ticker": "AAPL",
                            },
                        }
                    ]
                }
            }

            mock_es_instance.search.side_effect = [shared_response, shared_response]

            client = SearchClient(
                "http://localhost:9200",
                embedding_model_mock=True,
                default_rrf_k=RRF_K,
            )
            config = SearchConfig(limit=KNN_K_VALUE)

            results = await client.search_tool(
                query="revenue growth",
                search_type="hybrid",
                config=config,
            )

            # Should deduplicate and boost score
            assert len(results) == 1
            assert results[0].doc_id == "doc1"
            # RRF score should be higher than single ranking
            # Both at rank 1: 1/(60+1) + 1/(60+1) = 2/61
            expected_score = 2.0 / (RRF_K + 1)
            assert abs(results[0].score - expected_score) < RRF_TOLERANCE
