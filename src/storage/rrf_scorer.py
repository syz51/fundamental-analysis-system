"""Reciprocal Rank Fusion (RRF) scoring for search result merging."""

from collections import defaultdict

from storage.search_types import SearchResult


class RRFScorer:
    """
    Implements Reciprocal Rank Fusion algorithm for merging multiple search result lists.

    RRF combines rankings from different search strategies (e.g., keyword + semantic)
    by computing: Score = sum(1 / (k + rank)) where rank is 1-based.
    """

    def __init__(self, default_k: int = 60):
        """
        Initialize RRF scorer.

        Args:
            default_k: RRF constant for score calculation. Higher k reduces impact of rank differences.
        """
        if default_k <= 0:
            raise ValueError(f"RRF constant k must be positive, got {default_k}")
        self.default_k = default_k

    def merge(self, result_lists: list[list[SearchResult]], k: int | None = None) -> list[SearchResult]:
        """
        Combines multiple lists of SearchResults using Reciprocal Rank Fusion.

        Args:
            result_lists: List of search result lists to merge
            k: Optional RRF constant override. Uses default_k if not provided.

        Returns:
            Merged and sorted list of SearchResults with updated RRF scores

        Raises:
            ValueError: If k is not positive

        Implementation:
            Score = sum(1 / (k + rank)) where rank is 1-based (first result = rank 1).
            Uses enumerate (0-indexed) + 1 to achieve 1-based ranking.
        """
        k_value = k if k is not None else self.default_k

        if k_value <= 0:
            raise ValueError(f"RRF constant k must be positive, got {k_value}")

        fused_scores: dict[str, float] = defaultdict(float)
        doc_map = {}

        for r_list in result_lists:
            for rank, result in enumerate(r_list):
                fused_scores[result.doc_id] += 1.0 / (k_value + rank + 1)
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
