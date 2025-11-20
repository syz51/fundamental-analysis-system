"""
Error Handling Tests for Elasticsearch Search Tool

Tests retry logic, circuit breaker, and exception handling.
"""

import time
from unittest.mock import AsyncMock, Mock, patch

import pytest
from elastic_transport import ApiResponseMeta, HttpHeaders
from elasticsearch.exceptions import ApiError
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from storage.search_tool import CircuitBreaker, SearchClient, retry_with_backoff

pytestmark = pytest.mark.unit

# Test constants
FAILURE_THRESHOLD_LOW = 2
FAILURE_THRESHOLD_MED = 3
MAX_RETRIES_LOW = 2
MAX_RETRIES_MED = 3


# --- Test Helpers ---


def _create_api_error(message: str, status_code: int) -> ApiError:
    """Helper to create ApiError with proper meta structure."""
    meta = ApiResponseMeta(
        status_code,  # status
        "1.1",  # http_version
        HttpHeaders(),  # headers
        0.1,  # duration
        Mock(),  # node
    )
    return ApiError(message=message, meta=meta, body={})


# --- Circuit Breaker Tests ---


def test_circuit_breaker_initial_state() -> None:
    """Test circuit breaker starts in closed state."""
    cb = CircuitBreaker(failure_threshold=3, timeout=60)
    assert cb.state == "closed"
    assert cb.failures == 0
    assert cb.can_execute() is True


def test_circuit_breaker_opens_after_threshold() -> None:
    """Test circuit breaker opens after failure threshold."""
    cb = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD_MED, timeout=60)

    # Record failures
    cb.record_failure()
    assert cb.state == "closed"
    assert cb.failures == 1

    cb.record_failure()
    assert cb.state == "closed"
    assert cb.failures == FAILURE_THRESHOLD_LOW

    cb.record_failure()
    assert cb.state == "open"
    assert cb.failures == FAILURE_THRESHOLD_MED
    assert cb.can_execute() is False


def test_circuit_breaker_resets_on_success() -> None:
    """Test circuit breaker resets failures on success."""
    cb = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD_MED, timeout=60)

    cb.record_failure()
    cb.record_failure()
    assert cb.failures == FAILURE_THRESHOLD_LOW

    cb.record_success()
    assert cb.failures == 0
    assert cb.state == "closed"


def test_circuit_breaker_half_open_after_timeout() -> None:
    """Test circuit breaker enters half-open state after timeout."""
    cb = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD_LOW, timeout=0.1)  # 100ms timeout

    # Open circuit
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "open"

    # Wait for timeout
    time.sleep(0.2)

    # Should allow execution (half-open)
    assert cb.can_execute() is True
    assert cb.state == "half-open"


def test_circuit_breaker_half_open_stays_half_open() -> None:
    """Test circuit breaker returns True when already in half-open state."""
    cb = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD_LOW, timeout=0.1)

    # Manually set to half-open
    cb.state = "half-open"

    # Should return True and stay half-open
    assert cb.can_execute() is True
    assert cb.state == "half-open"


# --- Retry Decorator Tests ---


@pytest.mark.asyncio
async def test_retry_succeeds_first_attempt() -> None:
    """Test retry decorator when function succeeds on first attempt."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_MED, base_delay=0.01, max_delay=0.1)
    async def test_func() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = await test_func()
    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_retries() -> None:
    """Test retry decorator when function succeeds after failures."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_MED, base_delay=0.01, max_delay=0.1)
    async def test_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < MAX_RETRIES_MED:
            raise ESConnectionError("Connection failed")
        return "success"

    result = await test_func()
    assert result == "success"
    assert call_count == MAX_RETRIES_MED


@pytest.mark.asyncio
async def test_retry_exhausts_attempts() -> None:
    """Test retry decorator when all attempts fail."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_LOW, base_delay=0.01, max_delay=0.1)
    async def test_func() -> None:
        nonlocal call_count
        call_count += 1
        raise ESConnectionError("Connection failed")

    with pytest.raises(ESConnectionError):
        await test_func()

    assert call_count == MAX_RETRIES_MED  # Initial + 2 retries


@pytest.mark.asyncio
async def test_retry_rate_limit() -> None:
    """Test retry decorator handles 429 rate limiting."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_LOW, base_delay=0.01, max_delay=0.1)
    async def test_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < MAX_RETRIES_LOW:
            raise _create_api_error("Rate limited", 429)
        return "success"

    result = await test_func()
    assert result == "success"
    assert call_count == MAX_RETRIES_LOW


@pytest.mark.asyncio
async def test_retry_non_retryable_error() -> None:
    """Test retry decorator does not retry non-retryable errors."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_MED, base_delay=0.01, max_delay=0.1)
    async def test_func() -> None:
        nonlocal call_count
        call_count += 1
        raise ValueError("Invalid input")

    with pytest.raises(ValueError, match="Invalid input"):
        await test_func()

    assert call_count == 1  # No retries for ValueError


@pytest.mark.asyncio
async def test_retry_api_error_non_429() -> None:
    """Test retry decorator does not retry non-429 API errors."""
    call_count = 0

    @retry_with_backoff(max_retries=MAX_RETRIES_MED, base_delay=0.01, max_delay=0.1)
    async def test_func() -> None:
        nonlocal call_count
        call_count += 1
        raise _create_api_error("Bad request", 400)

    with pytest.raises(ApiError):
        await test_func()

    assert call_count == 1  # No retries for 400 error


# --- SearchClient Error Handling Tests ---


@pytest.mark.asyncio
async def test_search_circuit_breaker_blocks_request() -> None:
    """Test search_tool respects circuit breaker state."""
    client = SearchClient()

    # Open circuit breaker
    client.circuit_breaker.state = "open"

    with pytest.raises(RuntimeError, match="Circuit breaker is open"):
        await client.search_tool(query="test")


@pytest.mark.asyncio
async def test_search_connection_error_triggers_circuit_breaker() -> None:
    """Test connection errors trigger circuit breaker."""
    client = SearchClient()

    # Mock Elasticsearch client to raise ESConnectionError
    with patch.object(client.client, "search", side_effect=ESConnectionError("Connection failed")):
        with pytest.raises(ESConnectionError):
            await client.search_tool(query="test", search_type="keyword")

        # Circuit breaker should record failure
        # Note: retry decorator will call it 4 times (1 initial + 3 retries)
        # Each call records a failure, but circuit breaker threshold is 5
        assert client.circuit_breaker.failures > 0


@pytest.mark.asyncio
async def test_search_success_resets_circuit_breaker() -> None:
    """Test successful search resets circuit breaker failures."""
    client = SearchClient()

    # Pre-load some failures
    client.circuit_breaker.record_failure()
    client.circuit_breaker.record_failure()
    assert client.circuit_breaker.failures == FAILURE_THRESHOLD_LOW

    # Mock successful search
    mock_response = {
        "hits": {
            "hits": [
                {
                    "_id": "doc1",
                    "_index": "test",
                    "_score": 1.0,
                    "_source": {"text": "test content"},
                }
            ]
        }
    }

    with patch.object(client.client, "search", new=AsyncMock(return_value=mock_response)):
        await client.search_tool(query="test", search_type="keyword")

        # Circuit breaker should reset
        assert client.circuit_breaker.failures == 0
        assert client.circuit_breaker.state == "closed"


@pytest.mark.asyncio
async def test_search_api_error_does_not_trigger_circuit_breaker() -> None:
    """Test API errors (non-connection) don't trigger circuit breaker."""
    client = SearchClient()

    # Mock API error (400)
    api_error = _create_api_error("Bad query", 400)

    with patch.object(client.client, "search", side_effect=api_error):
        with pytest.raises(ApiError):
            await client.search_tool(query="test", search_type="keyword")

        # Circuit breaker should NOT record failure for API errors
        assert client.circuit_breaker.failures == 0


@pytest.mark.asyncio
async def test_hybrid_search_partial_failure() -> None:
    """Test hybrid search when one query fails."""
    client = SearchClient()

    mock_success = {
        "hits": {
            "hits": [
                {
                    "_id": "doc1",
                    "_index": "test",
                    "_score": 1.0,
                    "_source": {"text": "test"},
                }
            ]
        }
    }

    # Mock one query succeeding, one failing
    # Hybrid search makes 2 calls, and retry decorator will retry 3 times = 8 total calls
    mock_search = AsyncMock(
        side_effect=[
            mock_success,
            ESConnectionError("kNN failed"),  # First attempt
            mock_success,
            ESConnectionError("kNN failed"),  # Retry 1
            mock_success,
            ESConnectionError("kNN failed"),  # Retry 2
            mock_success,
            ESConnectionError("kNN failed"),  # Retry 3
        ]
    )
    with (
        patch.object(client.client, "search", new=mock_search),
        pytest.raises(ESConnectionError),
    ):
        await client.search_tool(query="test", search_type="hybrid")


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])
