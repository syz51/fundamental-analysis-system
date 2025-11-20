import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from elasticsearch import AsyncElasticsearch

if TYPE_CHECKING:
    from elastic_transport import ObjectApiResponse
from elasticsearch.exceptions import (
    ApiError,
    ConnectionTimeout,
    TransportError,
)
from elasticsearch.exceptions import (
    ConnectionError as ESConnectionError,
)

from storage.embedding_generator import EmbeddingGenerator
from storage.filter_builder import SearchFilterBuilder
from storage.rrf_scorer import RRFScorer
from storage.search_types import SearchConfig, SearchResult

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


class SearchClient:
    def __init__(
        self,
        es_url: str = "http://localhost:9200",
        embedding_model_mock: bool = True,
        default_rrf_k: int = 60,
    ):
        self.client = AsyncElasticsearch(hosts=[es_url])
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

        # Initialize utility components
        self.rrf_scorer = RRFScorer(default_k=default_rrf_k)
        self.filter_builder = SearchFilterBuilder()
        self.embedding_generator = EmbeddingGenerator(use_mock=embedding_model_mock)

    async def close(self) -> None:
        await self.client.close()

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
        filter_clauses = self.filter_builder.build(config.ticker, config.start_date, config.end_date, config.filters)

        # Log request context
        logger.info(
            f"Search request: query='{query[:50]}...', type={search_type}, "
            f"indices={indices}, ticker={config.ticker}, filters={config.filters}"
        )

        # Helper to parse ES response
        def parse_response(response: ObjectApiResponse[Any]) -> list[SearchResult]:
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
                keyword_body: dict[str, Any] = {
                    "size": config.limit,
                    "_source": {"excludes": ["embedding"]},
                    "query": {
                        "bool": {
                            "must": [{"match": {"text": query}}],
                            "filter": filter_clauses,
                        }
                    },
                }
                resp = await self.client.search(index=indices, **keyword_body)
                results = parse_response(resp)
                self.circuit_breaker.record_success()
                logger.info(f"Search successful: returned {len(results)} results")
                return results

            elif search_type == "semantic":
                vector = await self.embedding_generator.generate(query)
                semantic_body: dict[str, Any] = {
                    "size": config.limit,
                    "_source": {"excludes": ["embedding"]},
                    "knn": {
                        "field": "embedding",
                        "query_vector": vector,
                        "k": config.limit,
                        "num_candidates": 100,
                        "filter": filter_clauses,
                    },
                }
                resp = await self.client.search(index=indices, **semantic_body)
                results = parse_response(resp)
                self.circuit_breaker.record_success()
                logger.info(f"Search successful: returned {len(results)} results")
                return results

            elif search_type == "hybrid":
                # Execute BM25 and kNN in parallel
                vector = await self.embedding_generator.generate(query)

                # Query A: BM25
                bm25_body: dict[str, Any] = {
                    "size": config.limit,
                    "_source": {"excludes": ["embedding"]},
                    "query": {
                        "bool": {
                            "must": [{"match": {"text": query}}],
                            "filter": filter_clauses,
                        }
                    },
                }

                # Query B: kNN
                knn_body: dict[str, Any] = {
                    "size": config.limit,
                    "_source": {"excludes": ["embedding"]},
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
                results = self.rrf_scorer.merge([bm25_results, knn_results])
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
