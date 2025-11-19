import asyncio
import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, Literal, TypeVar

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    ApiError,
    ConnectionTimeout,
    TransportError,
)
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
)

logger = logging.getLogger(__name__)

# Constants
RATE_LIMIT_STATUS_CODE = 429

# Type variables for generic typing
T = TypeVar("T")


# --- Error Handling & Retry Logic ---


class CircuitBreaker:
    """Simple circuit breaker to prevent cascading failures."""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failures} consecutive failures")

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            # Check if timeout has passed
            if self.last_failure_time is not None and time.time() - self.last_failure_time >= self.timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        return self.state == "half-open"


def retry_with_backoff(
    max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Retry decorator with exponential backoff for async functions.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds (doubles each retry)
        max_delay: Maximum delay between retries
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except (ESConnectionError, ConnectionTimeout) as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
                except ApiError as e:
                    # Rate limiting (429) should be retried
                    if e.status_code == RATE_LIMIT_STATUS_CODE and attempt < max_retries:
                        last_exception = e
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"{func.__name__} rate limited (attempt {attempt + 1}/{max_retries + 1}). "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        # Other API errors should not be retried
                        logger.error(f"{func.__name__} API error: {e}")
                        raise
                except Exception as e:
                    # Non-retryable exceptions
                    logger.error(f"{func.__name__} non-retryable error: {e}")
                    raise

            # If we've exhausted all retries
            if last_exception is not None:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed after retries with unknown error")

        return wrapper

    return decorator


@dataclass
class SearchConfig:
    """Configuration for search filtering and pagination."""

    ticker: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    doc_types: list[str] | None = None
    filters: dict[str, Any] | None = None
    limit: int = 10


@dataclass
class SearchResult:
    doc_id: str
    score: float
    content: str
    metadata: dict[str, Any]
    source_index: str


class SearchClient:
    def __init__(
        self,
        es_url: str = "http://localhost:9200",
        embedding_model_mock: bool = True,
        default_rrf_k: int = 60,
    ):
        self.client = AsyncElasticsearch(hosts=[es_url])
        self.embedding_model_mock = embedding_model_mock
        self.default_rrf_k = default_rrf_k
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

    async def close(self) -> None:
        await self.client.close()

    async def _generate_embedding(self, text: str) -> list[float]:  # noqa: ARG002
        """
        Generates a 1536-dimensional embedding vector.

        TODO: Replace with actual call to OpenAI or local model.
        Currently unused parameter 'text' will be used when real embedding model is integrated.
        """
        if self.embedding_model_mock:
            # Return a random normalized vector or zero vector for testing
            # Using a simple deterministic pattern for now to avoid random import if not needed
            return [0.001] * 1536
        else:
            raise NotImplementedError("Real embedding model not configured")

    def _build_filters(
        self,
        ticker: str | None,
        start_date: str | None,
        end_date: str | None,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """
        Constructs Elasticsearch filter clauses.
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

    def _rrf_merge(self, result_lists: list[list[SearchResult]], k: int = 60) -> list[SearchResult]:
        """
        Combines multiple lists of SearchResults using Reciprocal Rank Fusion.

        Score = sum(1 / (k + rank)) where rank is 1-based (first result = rank 1).
        Implementation uses enumerate (0-indexed) + 1 to achieve 1-based ranking.
        """
        if k <= 0:
            raise ValueError(f"RRF constant k must be positive, got {k}")

        fused_scores: dict[str, float] = defaultdict(float)
        doc_map = {}

        for r_list in result_lists:
            for rank, result in enumerate(r_list):
                fused_scores[result.doc_id] += 1.0 / (k + rank + 1)
                if result.doc_id not in doc_map:
                    doc_map[result.doc_id] = result

        # Sort by fused score descending
        sorted_doc_ids = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)

        final_results = []
        for doc_id in sorted_doc_ids:
            original_result = doc_map[doc_id]
            # Update score to RRF score
            original_result.score = fused_scores[doc_id]
            final_results.append(original_result)

        return final_results

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def search_tool(
        self,
        query: str,
        search_type: Literal["keyword", "semantic", "hybrid"] = "hybrid",
        config: SearchConfig | None = None,
    ) -> list[SearchResult]:
        """
        Universal search across Elasticsearch indices using client-side RRF for hybrid search.

        Args:
            query: Search query string
            search_type: Type of search (keyword, semantic, or hybrid)
            config: Optional search configuration (filters, pagination, etc.)
        """
        # Circuit breaker check
        if not self.circuit_breaker.can_execute():
            raise RuntimeError(f"Circuit breaker is {self.circuit_breaker.state}. Service temporarily unavailable.")

        # Use default config if not provided
        if config is None:
            config = SearchConfig()

        # 1. Determine Indices
        indices = ",".join(config.doc_types) if config.doc_types else "sec_filings,transcripts,news"

        # 2. Build Filters (Shared)
        filter_clauses = self._build_filters(config.ticker, config.start_date, config.end_date, config.filters)

        # Log request context
        logger.info(
            f"Search request: query='{query[:50]}...', type={search_type}, "
            f"indices={indices}, ticker={config.ticker}, filters={config.filters}"
        )

        # Helper to parse ES response
        def parse_response(response: dict[str, Any]) -> list[SearchResult]:
            results = []
            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                score = hit.get("_score", 0.0) or 0.0
                results.append(
                    SearchResult(
                        doc_id=hit["_id"],
                        score=score,
                        content=source.get("text", ""),
                        metadata={k: v for k, v in source.items() if k != "text"},
                        source_index=hit["_index"],
                    )
                )
            return results

        # 3. Execute Search based on type
        try:
            if search_type == "keyword":
                body = {
                    "size": config.limit,
                    "_source": {"exclude": ["embedding"]},
                    "query": {
                        "bool": {
                            "must": [{"match": {"text": query}}],
                            "filter": filter_clauses,
                        }
                    },
                }
                resp = await self.client.search(index=indices, **body)
                results = parse_response(resp)
                self.circuit_breaker.record_success()
                logger.info(f"Search successful: returned {len(results)} results")
                return results

            elif search_type == "semantic":
                vector = await self._generate_embedding(query)
                body = {
                    "size": config.limit,
                    "_source": {"exclude": ["embedding"]},
                    "knn": {
                        "field": "embedding",
                        "query_vector": vector,
                        "k": config.limit,
                        "num_candidates": 100,
                        "filter": filter_clauses,
                    },
                }
                resp = await self.client.search(index=indices, **body)
                results = parse_response(resp)
                self.circuit_breaker.record_success()
                logger.info(f"Search successful: returned {len(results)} results")
                return results

            elif search_type == "hybrid":
                # Execute BM25 and kNN in parallel
                vector = await self._generate_embedding(query)

                # Query A: BM25
                bm25_body = {
                    "size": config.limit,
                    "_source": {"exclude": ["embedding"]},
                    "query": {
                        "bool": {
                            "must": [{"match": {"text": query}}],
                            "filter": filter_clauses,
                        }
                    },
                }

                # Query B: kNN
                knn_body = {
                    "size": config.limit,
                    "_source": {"exclude": ["embedding"]},
                    "knn": {
                        "field": "embedding",
                        "query_vector": vector,
                        "k": config.limit,
                        "num_candidates": 100,
                        "filter": filter_clauses,
                    },
                }

                # Run parallel
                bm25_resp, knn_resp = await asyncio.gather(
                    self.client.search(index=indices, **bm25_body),
                    self.client.search(index=indices, **knn_body),
                )

                bm25_results = parse_response(bm25_resp)
                knn_results = parse_response(knn_resp)

                # Merge with RRF
                results = self._rrf_merge([bm25_results, knn_results], k=self.default_rrf_k)
                self.circuit_breaker.record_success()
                logger.info(f"Hybrid search successful: returned {len(results)} results")
                return results

        except (ESConnectionError, ConnectionTimeout, TransportError) as e:
            self.circuit_breaker.record_failure()
            logger.error(
                f"Connection error during search: {type(e).__name__}: {e}. Query: '{query[:50]}...', indices: {indices}"
            )
            raise
        except ApiError as e:
            # Don't record API errors as circuit breaker failures (they're not infrastructure issues)
            logger.error(
                f"Elasticsearch API error: {e.status_code} - {e.message}. Query: '{query[:50]}...', indices: {indices}"
            )
            raise
        except Exception as e:
            self.circuit_breaker.record_failure()
            logger.error(
                f"Unexpected error during search: {type(e).__name__}: {e}. Query: '{query[:50]}...', indices: {indices}"
            )
            raise


# Example Usage (for testing)
async def main() -> None:
    client = SearchClient()
    try:
        # Ensure indices exist first (run elasticsearch_setup.py)
        config = SearchConfig(ticker="AAPL", limit=5)
        results = await client.search_tool(query="revenue growth", search_type="hybrid", config=config)
        for r in results:
            print(f"[{r.score:.4f}] {r.doc_id}: {r.content[:50]}...")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
