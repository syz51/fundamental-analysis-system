"""Extended unit tests for SearchClient integration tests."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from storage.search_tool import SearchClient, SearchConfig

# Test constants
EMBEDDING_DIMS = 1536
KNN_K_VALUE = 10
NUM_CANDIDATES = 100
RRF_K = 60
OVERLAP_COUNT = 2
RRF_TOLERANCE = 0.001

pytestmark = pytest.mark.unit


class TestSearchClientClose:
    """Tests for SearchClient.close() method."""

    @pytest.mark.asyncio
    async def test_close_calls_client_close(self) -> None:
        """close() should call the underlying Elasticsearch client close."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            client = SearchClient("http://localhost:9200")
            await client.close()

            # Verify close was called
            mock_es_instance.close.assert_called_once()


class TestSemanticSearch:
    """Tests for semantic search query structure (mocked)."""

    @pytest.mark.asyncio
    async def test_semantic_search_query_structure(self) -> None:
        """Semantic search builds correct kNN query."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
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
    async def test_semantic_search_with_filters(self) -> None:
        """Semantic search includes filter clauses in kNN query."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            mock_response: dict[str, Any] = {"hits": {"hits": []}}
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
    async def test_search_unexpected_exception_triggers_circuit_breaker(self) -> None:
        """Unexpected exceptions during search trigger circuit breaker."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
            mock_es_instance = AsyncMock()
            mock_es_class.return_value = mock_es_instance

            # Mock an unexpected exception
            mock_es_instance.search.side_effect = ValueError("Unexpected error")

            client = SearchClient("http://localhost:9200", embedding_model_mock=True)
            config = SearchConfig(limit=KNN_K_VALUE)

            # Mock asyncio.sleep to speed up retries
            with patch("asyncio.sleep"), pytest.raises(ValueError, match="Unexpected error"):
                await client.search_tool(
                    query="test query",
                    search_type="keyword",
                    config=config,
                )

            # Verify circuit breaker recorded failure
            assert client.circuit_breaker.failures >= 1


class TestHybridSearch:
    """Tests for hybrid search result merging."""

    @pytest.mark.asyncio
    async def test_hybrid_search_merges_results(self) -> None:
        """Hybrid search merges BM25 and kNN results using RRF."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
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
    async def test_hybrid_search_with_overlap(self) -> None:
        """Hybrid search correctly merges overlapping docs."""
        with patch("storage.search_tool.AsyncElasticsearch") as mock_es_class:
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
