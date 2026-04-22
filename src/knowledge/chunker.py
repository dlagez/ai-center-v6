from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from src.config.settings import settings
from src.parser.parser import markdown_to_text
from src.knowledge.schemas import DocumentChunk, ParsedDocument

DEFAULT_HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]


def chunk_document(
    document: ParsedDocument,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    resolved_chunk_size = settings.knowledge_chunk_size if chunk_size is None else chunk_size
    resolved_chunk_overlap = (
        settings.knowledge_chunk_overlap if chunk_overlap is None else chunk_overlap
    )

    if resolved_chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if resolved_chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if resolved_chunk_overlap >= resolved_chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    markdown = document.markdown.strip()
    if not markdown:
        return []

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=DEFAULT_HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=resolved_chunk_size,
        chunk_overlap=resolved_chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    header_docs = header_splitter.split_text(markdown)
    if not header_docs:
        header_docs = text_splitter.create_documents([markdown])

    chunks: list[DocumentChunk] = []
    for header_doc in header_docs:
        section_markdown = header_doc.page_content.strip()
        if not section_markdown:
            continue

        section_docs = text_splitter.create_documents(
            [section_markdown],
            metadatas=[header_doc.metadata],
        )
        for section_doc in section_docs:
            chunk_markdown = section_doc.page_content.strip()
            if not chunk_markdown:
                continue

            metadata = dict(section_doc.metadata)
            headers = [str(metadata[key]) for _, key in DEFAULT_HEADERS_TO_SPLIT_ON if metadata.get(key)]
            chunk_index = len(chunks)
            chunk_id = str(uuid5(NAMESPACE_URL, f"{document.doc_id}:{chunk_index}:{chunk_markdown}"))
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    doc_id=document.doc_id,
                    source=document.source,
                    index=chunk_index,
                    markdown=chunk_markdown,
                    text=markdown_to_text(chunk_markdown),
                    headers=headers,
                    metadata=metadata,
                )
            )

    return chunks
