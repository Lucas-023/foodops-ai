"""Semantic retrieval over ingested documents (Phase 3)."""


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Return the top-k chunks as {"text", "source", "score"}."""
    raise NotImplementedError("Semantic retrieval is implemented in Phase 3.")
