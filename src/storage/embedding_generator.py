"""Embedding generation for semantic search."""


class EmbeddingGenerator:
    """Generates embeddings for semantic search queries."""

    def __init__(self, use_mock: bool = True):
        """
        Initialize embedding generator.

        Args:
            use_mock: If True, use mock embeddings. If False, use real embedding model.
        """
        self.use_mock = use_mock

    async def generate(self, text: str) -> list[float]:  # noqa: ARG002
        """
        Generates a 1536-dimensional embedding vector.

        Args:
            text: Text to generate embedding for

        Returns:
            1536-dimensional embedding vector

        Note:
            TODO: Replace with actual call to OpenAI or local model.
            Currently unused parameter 'text' will be used when real embedding model is integrated.
        """
        if self.use_mock:
            # Return a simple deterministic pattern for testing
            # Using a simple deterministic pattern for now to avoid random import if not needed
            return [0.001] * 1536
        else:
            raise NotImplementedError("Real embedding model not configured")
