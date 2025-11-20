"""Test data factories for generating realistic test data.

Provides factory functions to create test documents, search results,
and other data structures used across unit and integration tests.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any


class SearchResultFactory:
    """Factory for creating SearchResult instances for testing."""

    @staticmethod
    def create(
        doc_id: str = "test_doc_001",
        score: float = 1.0,
        content: str = "Test document content",
        metadata: dict[str, Any] | None = None,
        source_index: str = "sec_filings",
    ) -> dict[str, Any]:
        """Create a search result dict (for mocking Elasticsearch responses)."""
        if metadata is None:
            metadata = {
                "ticker": "AAPL",
                "date": "2024-01-01",
                "doc_type": "10-K",
            }

        return {
            "_index": source_index,
            "_id": doc_id,
            "_score": score,
            "_source": {
                "doc_id": doc_id,
                "text": content,
                **metadata,
            },
        }

    @staticmethod
    def create_many(
        count: int = 5,
        base_score: float = 10.0,
        index: str = "sec_filings",
    ) -> list[dict[str, Any]]:
        """Create multiple search results with decreasing scores."""
        return [
            SearchResultFactory.create(
                doc_id=f"doc_{i}",
                score=base_score - i * 0.1,
                content=f"Test document {i} content",
                source_index=index,
            )
            for i in range(count)
        ]


class DocumentFactory:
    """Factory for creating Elasticsearch document structures."""

    @staticmethod
    def create_sec_filing(
        doc_id: str = "sec_001",
        ticker: str = "AAPL",
        filing_type: str = "10-K",
        fiscal_year: int = 2024,
        content: str = "Revenue increased by 15% year-over-year",
    ) -> dict[str, Any]:
        """Create SEC filing document."""
        return {
            "doc_id": doc_id,
            "doc_type": "sec_filing",
            "source": "SEC EDGAR",
            "ticker": ticker,
            "company_name": "Apple Inc.",
            "cik": "0000320193",
            "date": "2024-01-01T00:00:00Z",
            "fiscal_year": fiscal_year,
            "fiscal_quarter": "Q4",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "text": content,
            "embedding": [0.001] * 1536,  # Mock embedding
            "indexed_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            # SEC-specific fields
            "filing_type": filing_type,
            "accession_number": "0000320193-24-000001",
            "section": "MD&A",
            "url": f"https://www.sec.gov/Archives/edgar/data/320193/{doc_id}.htm",
            "file_size": 1024000,
            "revenue": 394328000000,
            "net_income": 96995000000,
            "market_cap": 3000000000000,
        }

    @staticmethod
    def create_transcript(
        doc_id: str = "trans_001",
        ticker: str = "MSFT",
        speaker: str = "CEO",
        content: str = "We delivered strong Q4 results",
    ) -> dict[str, Any]:
        """Create earnings call transcript document."""
        return {
            "doc_id": doc_id,
            "doc_type": "transcript",
            "source": "Earnings Call",
            "ticker": ticker,
            "company_name": "Microsoft Corporation",
            "cik": "0000789019",
            "date": "2024-01-25T00:00:00Z",
            "fiscal_year": 2024,
            "fiscal_quarter": "Q4",
            "sector": "Technology",
            "industry": "Software",
            "text": content,
            "embedding": [0.002] * 1536,  # Mock embedding
            "indexed_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            # Transcript-specific fields
            "call_type": "earnings",
            "speaker": speaker,
            "speaker_role": "C-Level",
            "segment": "Q&A",
            "duration_seconds": 3600,
            "sentiment_score": 0.75,
        }

    @staticmethod
    def create_news(
        doc_id: str = "news_001",
        ticker: str = "GOOGL",
        headline: str = "Google announces new AI features",
        content: str = "Google revealed new AI capabilities today",
    ) -> dict[str, Any]:
        """Create news article document."""
        return {
            "doc_id": doc_id,
            "doc_type": "news",
            "source": "Reuters",
            "ticker": ticker,
            "company_name": "Alphabet Inc.",
            "cik": "0001652044",
            "date": "2024-02-01T10:30:00Z",
            "fiscal_year": 2024,
            "fiscal_quarter": "Q1",
            "sector": "Technology",
            "industry": "Internet Services",
            "text": content,
            "embedding": [0.003] * 1536,  # Mock embedding
            "indexed_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            # News-specific fields
            "headline": headline,
            "author": "Jane Smith",
            "publication": "Reuters",
            "url": "https://www.reuters.com/technology/google-ai-2024-02-01/",
            "word_count": 500,
            "event_type": "product_launch",
            "mentioned_tickers": [ticker, "MSFT", "META"],
        }

    @staticmethod
    def create_batch(
        doc_type: str = "sec_filing",
        count: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Create multiple documents of the same type."""
        factory_map: dict[str, Callable[..., dict[str, Any]]] = {
            "sec_filing": DocumentFactory.create_sec_filing,
            "transcript": DocumentFactory.create_transcript,
            "news": DocumentFactory.create_news,
        }

        factory: Callable[..., dict[str, Any]] = factory_map.get(doc_type, DocumentFactory.create_sec_filing)

        return [factory(doc_id=f"{doc_type}_{i:03d}", **kwargs) for i in range(count)]


class ElasticsearchResponseFactory:
    """Factory for creating mock Elasticsearch API responses."""

    @staticmethod
    def search_response(
        hits: list[dict[str, Any]],
        total: int | None = None,
        max_score: float | None = None,
    ) -> dict[str, Any]:
        """Create Elasticsearch search response."""
        if total is None:
            total = len(hits)
        if max_score is None and hits:
            max_score = hits[0].get("_score", 1.0)

        return {
            "took": 5,
            "timed_out": False,
            "_shards": {
                "total": 3,
                "successful": 3,
                "skipped": 0,
                "failed": 0,
            },
            "hits": {
                "total": {"value": total, "relation": "eq"},
                "max_score": max_score,
                "hits": hits,
            },
        }

    @staticmethod
    def index_response(
        doc_id: str,
        index: str = "sec_filings",
        result: str = "created",
    ) -> dict[str, Any]:
        """Create Elasticsearch index response."""
        return {
            "_index": index,
            "_id": doc_id,
            "_version": 1,
            "result": result,
            "_shards": {"total": 3, "successful": 2, "failed": 0},
            "_seq_no": 0,
            "_primary_term": 1,
        }

    @staticmethod
    def bulk_response(
        success_count: int = 100,
        error_count: int = 0,
    ) -> dict[str, Any]:
        """Create Elasticsearch bulk response."""
        items = []

        # Add successful items
        for i in range(success_count):
            items.append(
                {
                    "index": {
                        "_index": "sec_filings",
                        "_id": f"doc_{i}",
                        "_version": 1,
                        "result": "created",
                        "status": 201,
                    }
                }
            )

        # Add error items
        for i in range(error_count):
            items.append(
                {
                    "index": {
                        "_index": "sec_filings",
                        "_id": f"error_{i}",
                        "status": 400,
                        "error": {
                            "type": "mapper_parsing_exception",
                            "reason": "failed to parse field",
                        },
                    }
                }
            )

        return {
            "took": 30,
            "errors": error_count > 0,
            "items": items,
        }


class PostgresDataFactory:
    """Factory for creating PostgreSQL test data."""

    @staticmethod
    def create_company(
        ticker: str = "AAPL",
        name: str = "Apple Inc.",
        cik: str = "0000320193",
    ) -> dict[str, Any]:
        """Create company record."""
        return {
            "ticker": ticker,
            "name": name,
            "cik": cik,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3000000000000,
            "founded": 1976,
            "headquarters": "Cupertino, CA",
            "employees": 161000,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }


class RedisDataFactory:
    """Factory for creating Redis test data."""

    @staticmethod
    def create_cache_key(
        query: str = "revenue growth",
        search_type: str = "hybrid",
        ticker: str | None = None,
    ) -> str:
        """Create cache key for search results."""
        parts = [f"search:{search_type}:{query}"]
        if ticker:
            parts.append(f"ticker:{ticker}")
        return ":".join(parts)

    @staticmethod
    def create_agent_memory(
        agent_id: str = "agent_001",
        memory_type: str = "working",
    ) -> dict[str, Any]:
        """Create agent memory structure."""
        return {
            "agent_id": agent_id,
            "memory_type": memory_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "current_task": "analyzing_financials",
                "findings": ["Revenue up 15%", "Margins stable"],
                "confidence": 0.85,
            },
        }
