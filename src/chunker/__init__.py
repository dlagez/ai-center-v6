"""Chunker package."""

from src.chunker.chunker import chunk_document
from src.chunker.tender_chunker import chunk_tender_document

__all__ = ["chunk_document", "chunk_tender_document"]
