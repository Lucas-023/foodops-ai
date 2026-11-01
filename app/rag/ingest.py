"""Document ingestion (Phase 3): load data/docs, chunk, embed, store in ChromaDB."""

from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parents[2] / "data" / "docs"


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    if size <= overlap:
        raise ValueError("size must be greater than overlap")
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start : start + size])
        start += size - overlap
    return chunks


def ingest(docs_dir: Path = DOCS_DIR) -> None:
    raise NotImplementedError("Embedding and ChromaDB storage are implemented in Phase 3.")
