"""Tests for EmbeddingGenerator."""

import pytest

from storage.embedding_generator import EmbeddingGenerator

# Test constants
EMBEDDING_DIMS = 1536
MOCK_EMBEDDING_VALUE = 0.001

pytestmark = pytest.mark.unit


class TestGenerateEmbedding:
    """Tests for EmbeddingGenerator.generate() method."""

    @pytest.mark.asyncio
    async def test_generate_embedding_mock_mode(self) -> None:
        """In mock mode, returns deterministic 1536-dim vector."""
        generator = EmbeddingGenerator(use_mock=True)
        vector = await generator.generate("test query")

        assert isinstance(vector, list)
        assert len(vector) == EMBEDDING_DIMS
        assert all(v == MOCK_EMBEDDING_VALUE for v in vector)

    @pytest.mark.asyncio
    async def test_generate_embedding_real_mode_not_implemented(self) -> None:
        """When mock=False, raises NotImplementedError."""
        generator = EmbeddingGenerator(use_mock=False)

        with pytest.raises(NotImplementedError, match="Real embedding model not configured"):
            await generator.generate("test query")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
