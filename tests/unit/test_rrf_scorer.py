"""
RRF (Reciprocal Rank Fusion) Scoring Tests

Tests the RRFScorer class with known inputs to validate scoring correctness.
"""

import pytest

from storage.rrf_scorer import RRFScorer
from storage.search_types import SearchResult

pytestmark = pytest.mark.unit

# Test constants
PRECISION_THRESHOLD = 0.001  # Tolerance for floating-point score comparisons
EXPECTED_NO_OVERLAP_COUNT = 4  # Expected docs when merging 2+2 disjoint sets
EXPECTED_COMPLETE_OVERLAP_COUNT = 2  # Expected docs when merging identical sets


def create_search_result(doc_id: str, score: float, content: str = "test") -> SearchResult:
    """Helper to create SearchResult instances."""
    return SearchResult(
        doc_id=doc_id,
        score=score,
        content=content,
        metadata={},
        source_index="test_index",
    )


def test_rrf_merge_basic() -> None:
    """Test basic RRF merge with two result lists."""
    scorer = RRFScorer(default_k=60)

    # List 1: BM25 results
    list1 = [
        create_search_result("doc1", 10.0),  # rank 1
        create_search_result("doc2", 8.0),  # rank 2
        create_search_result("doc3", 5.0),  # rank 3
    ]

    # List 2: kNN results
    list2 = [
        create_search_result("doc2", 0.95),  # rank 1
        create_search_result("doc4", 0.90),  # rank 2
        create_search_result("doc1", 0.85),  # rank 3
    ]

    merged = scorer.merge([list1, list2])

    # Calculate expected scores (1-based ranking: rank+1)
    # doc1: 1/(60+1) + 1/(60+3) = 1/61 + 1/63 = 0.0164 + 0.0159 = 0.0323
    # doc2: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 = 0.0161 + 0.0164 = 0.0325
    # doc3: 1/(60+3) + 0        = 1/63         = 0.0159
    # doc4: 0        + 1/(60+2) = 1/62         = 0.0161

    # Expected order: doc2, doc1, doc4, doc3
    assert merged[0].doc_id == "doc2", f"Expected doc2 first, got {merged[0].doc_id}"
    assert merged[1].doc_id == "doc1", f"Expected doc1 second, got {merged[1].doc_id}"
    assert merged[2].doc_id == "doc4", f"Expected doc4 third, got {merged[2].doc_id}"
    assert merged[3].doc_id == "doc3", f"Expected doc3 fourth, got {merged[3].doc_id}"

    # Verify score calculations (approximate)
    assert abs(merged[0].score - 0.0325) < PRECISION_THRESHOLD, f"doc2 score incorrect: {merged[0].score}"
    assert abs(merged[1].score - 0.0323) < PRECISION_THRESHOLD, f"doc1 score incorrect: {merged[1].score}"
    assert abs(merged[2].score - 0.0161) < PRECISION_THRESHOLD, f"doc4 score incorrect: {merged[2].score}"
    assert abs(merged[3].score - 0.0159) < PRECISION_THRESHOLD, f"doc3 score incorrect: {merged[3].score}"


def test_rrf_merge_single_list() -> None:
    """Test RRF merge with single result list (should preserve order)."""
    scorer = RRFScorer(default_k=60)

    list1 = [
        create_search_result("doc1", 10.0),
        create_search_result("doc2", 8.0),
        create_search_result("doc3", 5.0),
    ]

    merged = scorer.merge([list1])

    # Order should be preserved
    assert merged[0].doc_id == "doc1"
    assert merged[1].doc_id == "doc2"
    assert merged[2].doc_id == "doc3"

    # Scores should be 1/(k+rank) with 1-based ranking
    assert abs(merged[0].score - 1 / 61) < PRECISION_THRESHOLD
    assert abs(merged[1].score - 1 / 62) < PRECISION_THRESHOLD
    assert abs(merged[2].score - 1 / 63) < PRECISION_THRESHOLD


def test_rrf_merge_no_overlap() -> None:
    """Test RRF merge with completely disjoint result sets."""
    scorer = RRFScorer(default_k=60)

    list1 = [
        create_search_result("doc1", 10.0),
        create_search_result("doc2", 8.0),
    ]

    list2 = [
        create_search_result("doc3", 0.95),
        create_search_result("doc4", 0.90),
    ]

    merged = scorer.merge([list1, list2])

    # All docs should appear
    assert len(merged) == EXPECTED_NO_OVERLAP_COUNT
    doc_ids = {r.doc_id for r in merged}
    assert doc_ids == {"doc1", "doc2", "doc3", "doc4"}


def test_rrf_merge_complete_overlap() -> None:
    """Test RRF merge with identical result sets."""
    scorer = RRFScorer(default_k=60)

    list1 = [
        create_search_result("doc1", 10.0),
        create_search_result("doc2", 8.0),
    ]

    list2 = [
        create_search_result("doc1", 0.95),
        create_search_result("doc2", 0.90),
    ]

    merged = scorer.merge([list1, list2])

    # Should have 2 docs (overlap)
    assert len(merged) == EXPECTED_COMPLETE_OVERLAP_COUNT
    assert merged[0].doc_id == "doc1"
    assert merged[1].doc_id == "doc2"

    # Scores should be doubled (both lists contribute)
    expected_doc1 = 1 / 61 + 1 / 61  # 2/(k+1)
    expected_doc2 = 1 / 62 + 1 / 62  # 2/(k+2)
    assert abs(merged[0].score - expected_doc1) < PRECISION_THRESHOLD
    assert abs(merged[1].score - expected_doc2) < PRECISION_THRESHOLD


def test_rrf_merge_different_k_values() -> None:
    """Test RRF merge with different k constants."""
    scorer = RRFScorer(default_k=60)

    list1 = [create_search_result("doc1", 10.0)]
    list2 = [create_search_result("doc1", 0.95)]

    # Test k=60 (default)
    merged_60 = scorer.merge([list1, list2])
    expected_60 = 1 / 61 + 1 / 61
    assert abs(merged_60[0].score - expected_60) < PRECISION_THRESHOLD

    # Test k=1 (very aggressive fusion)
    merged_1 = scorer.merge([list1, list2], k=1)
    expected_1 = 1 / 2 + 1 / 2  # (k=1, rank=1) -> 1/(1+1) = 0.5 each
    assert abs(merged_1[0].score - expected_1) < PRECISION_THRESHOLD

    # Test k=100 (more conservative fusion)
    merged_100 = scorer.merge([list1, list2], k=100)
    expected_100 = 1 / 101 + 1 / 101
    assert abs(merged_100[0].score - expected_100) < PRECISION_THRESHOLD


def test_rrf_merge_ranking_bias() -> None:
    """Test that RRF properly handles ranking bias (top results matter more)."""
    scorer = RRFScorer(default_k=60)

    # Doc1 appears 1st in both lists (strong signal)
    # Doc2 appears 1st in list1, 10th in list2 (mixed signal)
    # Doc3 appears 10th in both lists (weak signal)
    list1 = (
        [
            create_search_result("doc1", 100.0),
            create_search_result("doc2", 90.0),
        ]
        + [create_search_result(f"filler{i}", 80 - i) for i in range(8)]
        + [create_search_result("doc3", 10.0)]
    )

    list2 = (
        [
            create_search_result("doc1", 0.99),
        ]
        + [create_search_result(f"other{i}", 0.90 - i * 0.05) for i in range(8)]
        + [
            create_search_result("doc2", 0.50),
            create_search_result("doc3", 0.49),
        ]
    )

    merged = scorer.merge([list1, list2])

    # doc1 should be first (rank 1+1 in both lists)
    assert merged[0].doc_id == "doc1"

    # Find positions of doc2 and doc3
    doc2_pos = next(i for i, r in enumerate(merged) if r.doc_id == "doc2")
    doc3_pos = next(i for i, r in enumerate(merged) if r.doc_id == "doc3")

    # doc2 should rank higher than doc3 (better rank in list1)
    assert doc2_pos < doc3_pos, f"doc2 (pos {doc2_pos}) should rank higher than doc3 (pos {doc3_pos})"


def test_rrf_merge_invalid_k() -> None:
    """Test RRF merge with invalid k value."""
    # Test invalid k in constructor
    with pytest.raises(ValueError, match="RRF constant k must be positive"):
        RRFScorer(default_k=0)

    with pytest.raises(ValueError, match="RRF constant k must be positive"):
        RRFScorer(default_k=-5)

    # Test invalid k in merge method
    scorer = RRFScorer(default_k=60)
    list1 = [create_search_result("doc1", 10.0)]

    with pytest.raises(ValueError, match="RRF constant k must be positive"):
        scorer.merge([list1], k=0)

    with pytest.raises(ValueError, match="RRF constant k must be positive"):
        scorer.merge([list1], k=-5)


def test_rrf_merge_empty_lists() -> None:
    """Test RRF merge with empty input lists."""
    scorer = RRFScorer(default_k=60)

    # Empty lists should return empty result
    merged = scorer.merge([])
    assert merged == []

    # Single empty list
    merged = scorer.merge([[]])
    assert merged == []

    # Mix of empty and non-empty
    list1 = [create_search_result("doc1", 10.0)]
    merged = scorer.merge([list1, []])
    assert len(merged) == 1
    assert merged[0].doc_id == "doc1"


if __name__ == "__main__":
    # Run tests manually
    pytest.main([__file__, "-v"])
