"""Pytest configuration and fixtures for unit tests."""

from collections.abc import Callable
from typing import Any

import pytest

from storage.search_tool import SearchClient
from storage.search_types import SearchResult


@pytest.fixture
def search_client() -> SearchClient:
    """Provide a SearchClient instance for unit tests."""
    return SearchClient()


@pytest.fixture
def search_result_factory() -> Callable[..., SearchResult]:
    """Factory fixture for creating SearchResult instances in tests."""

    def _create_search_result(
        doc_id: str,
        score: float,
        content: str = "test content",
        metadata: dict[str, Any] | None = None,
        source_index: str = "test_index",
    ) -> SearchResult:
        """Helper to create SearchResult instances."""
        return SearchResult(
            doc_id=doc_id,
            score=score,
            content=content,
            metadata=metadata or {},
            source_index=source_index,
        )

    return _create_search_result
