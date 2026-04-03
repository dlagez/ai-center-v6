from src.knowledge.schemas import DocumentChunk, ParsedDocument


def chunk_document(
    document: ParsedDocument,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> list[DocumentChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    text = document.text
    if not text:
        return []

    chunks: list[DocumentChunk] = []
    start = 0
    index = 0
    step = chunk_size - chunk_overlap

    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(
            DocumentChunk(
                source=document.source,
                index=index,
                text=text[start:end],
            )
        )
        if end >= len(text):
            break
        start += step
        index += 1

    return chunks
