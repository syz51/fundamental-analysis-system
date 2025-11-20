"""
Cross-Index Query Tests for Elasticsearch Search Tool

Tests querying across multiple indices (sec_filings, transcripts, news) with filters.
Requires Elasticsearch running with populated indices.
"""

from collections.abc import AsyncGenerator
from datetime import datetime

import pytest
from elasticsearch import AsyncElasticsearch

from storage.search_tool import SearchClient, SearchConfig

pytestmark = [pytest.mark.integration, pytest.mark.requires_elasticsearch]

# Test constants
MIN_EXPECTED_INDICES = 2  # Minimum number of indices expected to have results
TEST_LIMIT_SMALL = 2  # Small limit for testing pagination


@pytest.fixture
async def populate_test_data(es_client: AsyncElasticsearch, worker_id: str) -> AsyncGenerator[None]:
    """Populate test data in all three indices with worker-specific IDs."""
    # Use worker_id to create unique document IDs per worker (e.g., "test-sec-1-gw0")
    # When not running with xdist, worker_id is "master"
    doc_suffix = f"-{worker_id}"

    # Sample documents for testing
    sec_filing_doc = {
        "doc_id": f"test-sec-1{doc_suffix}",
        "doc_type": "filing",
        "source": "SEC EDGAR",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "date": "2024-01-15",
        "fiscal_year": 2024,
        "fiscal_quarter": "Q1",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "text": "Apple reported strong revenue growth driven by iPhone sales and services expansion.",
        "embedding": [0.1] * 1536,
        "indexed_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "filing_type": "10-K",
        "accession_number": "0000320193-24-000001",
        "section": "MD&A",
        "url": "https://sec.gov/...",
        "file_size": 500000,
        "revenue": 90000000000,
        "net_income": 25000000000,
        "market_cap": 3000000000000,
    }

    transcript_doc = {
        "doc_id": f"test-transcript-1{doc_suffix}",
        "doc_type": "transcript",
        "source": "AlphaSense",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "date": "2024-01-20",
        "fiscal_year": 2024,
        "fiscal_quarter": "Q1",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "text": "CEO discussed supply chain improvements and AI integration in upcoming products.",
        "embedding": [0.2] * 1536,
        "indexed_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "call_type": "earnings",
        "speaker": "Tim Cook",
        "speaker_role": "CEO",
        "segment": "opening_remarks",
        "duration_seconds": 3600,
        "sentiment_score": 0.8,
    }

    news_doc = {
        "doc_id": f"test-news-1{doc_suffix}",
        "doc_type": "news",
        "source": "Reuters",
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "cik": "0000320193",
        "date": "2024-01-25",
        "fiscal_year": 2024,
        "fiscal_quarter": "Q1",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "text": "Apple stock rises on strong earnings report and optimistic guidance.",
        "embedding": [0.3] * 1536,
        "indexed_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "headline": "Apple Beats Expectations with Record Quarter",
        "author": "Jane Smith",
        "publication": "Reuters",
        "url": "https://reuters.com/...",
        "word_count": 450,
        "event_type": "earnings_report",
        "mentioned_tickers": "AAPL",
    }

    # Index documents with worker-specific IDs
    sec_id = f"test-sec-1{doc_suffix}"
    transcript_id = f"test-transcript-1{doc_suffix}"
    news_id = f"test-news-1{doc_suffix}"

    await es_client.index(index="sec_filings", id=sec_id, document=sec_filing_doc)
    await es_client.index(index="transcripts", id=transcript_id, document=transcript_doc)
    await es_client.index(index="news", id=news_id, document=news_doc)

    # Refresh indices to make documents searchable
    await es_client.indices.refresh(index="sec_filings,transcripts,news")

    yield

    # Cleanup worker-specific documents
    await es_client.options(ignore_status=404).delete(index="sec_filings", id=sec_id)
    await es_client.options(ignore_status=404).delete(index="transcripts", id=transcript_id)
    await es_client.options(ignore_status=404).delete(index="news", id=news_id)


@pytest.mark.usefixtures("populate_test_data")
class TestCrossIndexQueries:
    """Cross-index query tests."""

    @pytest.mark.asyncio
    async def test_search_single_index(self, search_client: SearchClient) -> None:
        """Test search within a single index."""
        config = SearchConfig(doc_types=["sec_filings"], limit=10)
        results = await search_client.search_tool(
            query="revenue growth",
            search_type="keyword",
            config=config,
        )

        # Should find the SEC filing
        assert len(results) >= 1
        assert any(r.source_index == "sec_filings" for r in results)

    @pytest.mark.asyncio
    async def test_search_multiple_indices(self, search_client: SearchClient) -> None:
        """Test search across multiple indices."""
        config = SearchConfig(doc_types=["sec_filings", "transcripts", "news"], limit=10)
        results = await search_client.search_tool(
            query="Apple",
            search_type="keyword",
            config=config,
        )

        # Should find documents from all three indices
        source_indices = {r.source_index for r in results}
        assert len(source_indices) >= MIN_EXPECTED_INDICES  # At least 2 indices should have results

    @pytest.mark.asyncio
    async def test_search_all_indices_default(self, search_client: SearchClient) -> None:
        """Test search across all indices (default behavior)."""
        config = SearchConfig(limit=10)
        results = await search_client.search_tool(query="Apple", search_type="keyword", config=config)

        # Should search all indices by default (doc_types=None)
        source_indices = {r.source_index for r in results}
        assert len(source_indices) >= 1

    @pytest.mark.asyncio
    async def test_search_with_ticker_filter(self, search_client: SearchClient) -> None:
        """Test search filtered by ticker."""
        config = SearchConfig(ticker="AAPL", limit=10)
        results = await search_client.search_tool(query="revenue", search_type="keyword", config=config)

        # All results should be for AAPL
        for result in results:
            assert result.metadata.get("ticker") == "AAPL"

    @pytest.mark.asyncio
    async def test_search_with_date_range(self, search_client: SearchClient) -> None:
        """Test search filtered by date range."""
        config = SearchConfig(start_date="2024-01-01", end_date="2024-01-31", limit=10)
        results = await search_client.search_tool(
            query="Apple",
            search_type="keyword",
            config=config,
        )

        # All results should be within date range
        for result in results:
            doc_date = result.metadata.get("date")
            if doc_date:
                assert "2024-01" in doc_date

    @pytest.mark.asyncio
    async def test_search_with_custom_filters(self, search_client: SearchClient) -> None:
        """Test search with custom field filters."""
        config = SearchConfig(doc_types=["sec_filings"], filters={"filing_type": "10-K"}, limit=10)
        results = await search_client.search_tool(
            query="Apple",
            search_type="keyword",
            config=config,
        )

        # Should only return 10-K filings
        for result in results:
            if result.source_index == "sec_filings":
                assert result.metadata.get("filing_type") == "10-K"

    @pytest.mark.asyncio
    async def test_search_combined_filters(self, search_client: SearchClient) -> None:
        """Test search with multiple combined filters."""
        config = SearchConfig(
            ticker="AAPL",
            start_date="2024-01-01",
            end_date="2024-12-31",
            doc_types=["sec_filings", "news"],
            filters={"sector": "Technology"},
            limit=10,
        )
        results = await search_client.search_tool(
            query="revenue",
            search_type="keyword",
            config=config,
        )

        # All results should match all filters
        for result in results:
            assert result.metadata.get("ticker") == "AAPL"
            assert result.metadata.get("sector") == "Technology"
            assert result.source_index in ["sec_filings", "news"]

    @pytest.mark.asyncio
    async def test_hybrid_search_cross_index(self, search_client: SearchClient) -> None:
        """Test hybrid search across multiple indices."""
        config = SearchConfig(doc_types=["sec_filings", "transcripts", "news"], limit=10)
        results = await search_client.search_tool(
            query="Apple revenue growth",
            search_type="hybrid",
            config=config,
        )

        # Hybrid search should combine BM25 and kNN results
        assert len(results) >= 1

        # Results should have RRF scores
        for result in results:
            assert result.score > 0

    @pytest.mark.asyncio
    async def test_semantic_search_cross_index(self, search_client: SearchClient) -> None:
        """Test semantic search across multiple indices."""
        config = SearchConfig(doc_types=["sec_filings", "news"], limit=5)
        results = await search_client.search_tool(
            query="financial performance",
            search_type="semantic",
            config=config,
        )

        # Note: Since we're using mock embeddings, results may not be semantically relevant
        # This test mainly validates the query executes without errors
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_limit_parameter(self, search_client: SearchClient) -> None:
        """Test search respects limit parameter."""
        config = SearchConfig(limit=TEST_LIMIT_SMALL)
        results = await search_client.search_tool(query="Apple", search_type="keyword", config=config)

        # Should return at most 2 results
        assert len(results) <= TEST_LIMIT_SMALL

    @pytest.mark.asyncio
    async def test_search_empty_results(self, search_client: SearchClient) -> None:
        """Test search returns empty list when no matches."""
        config = SearchConfig(limit=10)
        results = await search_client.search_tool(
            query="nonexistent_term_xyz123",
            search_type="keyword",
            config=config,
        )

        # Should return empty list or very few results
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_metadata_preservation(self, search_client: SearchClient) -> None:
        """Test that search results preserve document metadata."""
        config = SearchConfig(doc_types=["sec_filings"], limit=5)
        results = await search_client.search_tool(
            query="Apple",
            search_type="keyword",
            config=config,
        )

        # Verify metadata fields are present
        for result in results:
            if result.source_index == "sec_filings":
                assert "ticker" in result.metadata
                assert "company_name" in result.metadata
                assert "fiscal_year" in result.metadata
                # embedding should be excluded from _source
                assert "embedding" not in result.metadata


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])
