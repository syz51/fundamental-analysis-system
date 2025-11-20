"""Search-related data types and configurations."""

from dataclasses import dataclass
from typing import Any


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
    """Search result data structure."""

    doc_id: str
    score: float
    content: str
    metadata: dict[str, Any]
    source_index: str
