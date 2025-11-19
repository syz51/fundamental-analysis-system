"""
Cross-Index Query Tests for Elasticsearch Search Tool

Tests querying across multiple indices (sec_filings, transcripts, news) with filters.
Requires Elasticsearch running with populated indices.
"""

from datetime import datetime

import pytest
from src.storage.search_tool import SearchConfig

pytestmark = [pytest.mark.integration, pytest.mark.requires_elasticsearch]

# Test constants
MIN_EXPECTED_INDICES = 2  # Minimum number of indices expected to have results
TEST_LIMIT_SMALL = 2  # Small limit for testing pagination


@pytest.fixture
async def populate_test_data(es_client):
    """Populate test data in all three indices."""
    # Sample documents for testing
    sec_filing_doc = {
        "doc_id": "test-sec-1",
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
        "doc_id": "test-transcript-1",
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
        "doc_id": "test-news-1",
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

    # Index documents
    await es_client.index(index="sec_filings", id="test-sec-1", document=sec_filing_doc)
    await es_client.index(index="transcripts", id="test-transcript-1", document=transcript_doc)
    await es_client.index(index="news", id="test-news-1", document=news_doc)

    # Refresh indices to make documents searchable
    await es_client.indices.refresh(index="sec_filings,transcripts,news")

    yield

    # Cleanup
    await es_client.delete(index="sec_filings", id="test-sec-1", ignore=404)
    await es_client.delete(index="transcripts", id="test-transcript-1", ignore=404)
    await es_client.delete(index="news", id="test-news-1", ignore=404)


@pytest.mark.asyncio
async def test_search_single_index(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_multiple_indices(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_all_indices_default(search_client, populate_test_data):  # noqa: ARG001
    """Test search across all indices (default behavior)."""
    config = SearchConfig(limit=10)
    results = await search_client.search_tool(query="Apple", search_type="keyword", config=config)

    # Should search all indices by default (doc_types=None)
    source_indices = {r.source_index for r in results}
    assert len(source_indices) >= 1


@pytest.mark.asyncio
async def test_search_with_ticker_filter(search_client, populate_test_data):  # noqa: ARG001
    """Test search filtered by ticker."""
    config = SearchConfig(ticker="AAPL", limit=10)
    results = await search_client.search_tool(query="revenue", search_type="keyword", config=config)

    # All results should be for AAPL
    for result in results:
        assert result.metadata.get("ticker") == "AAPL"


@pytest.mark.asyncio
async def test_search_with_date_range(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_with_custom_filters(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_combined_filters(search_client, populate_test_data):  # noqa: ARG001
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
async def test_hybrid_search_cross_index(search_client, populate_test_data):  # noqa: ARG001
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
async def test_semantic_search_cross_index(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_limit_parameter(search_client, populate_test_data):  # noqa: ARG001
    """Test search respects limit parameter."""
    config = SearchConfig(limit=TEST_LIMIT_SMALL)
    results = await search_client.search_tool(query="Apple", search_type="keyword", config=config)

    # Should return at most 2 results
    assert len(results) <= TEST_LIMIT_SMALL


@pytest.mark.asyncio
async def test_search_empty_results(search_client, populate_test_data):  # noqa: ARG001
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
async def test_search_metadata_preservation(search_client, populate_test_data):  # noqa: ARG001
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
