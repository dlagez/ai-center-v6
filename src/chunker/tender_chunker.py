import re
from dataclasses import dataclass, field
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter

from docling_core.transforms.chunker.hierarchical_chunker import HierarchicalChunker
from src.config.settings import settings
from src.knowledge.schemas import DocumentChunk, ParsedDocument
from src.parser.parser import markdown_to_text

CATALOG_PREFIX_RE = re.compile(r"^\s*(\d+-\d+)\s+(.+)$")
CHAPTER_RE = re.compile(r"^\s*第[一二三四五六七八九十百零]+章\s*.+$")
SECTION_RE = re.compile(r"^\s*[一二三四五六七八九十]+[、.]\s*.+$")
CLAUSE_RE = re.compile(r"^\s*\d+(?:\.\d+){1,3}\s+.*$")
SUBITEM_RE = re.compile(r"^\s*[（(][一二三四五六七八九十]+[)）]\s*.+$")
SPECIAL_RE = re.compile(
    r"^\s*(备注[:：]?|附件[:：]?|评分标准|需要补充的其他内容|申请人资质条件、能力和信誉)\s*$"
)


@dataclass
class TenderChunkCandidate:
    marker_type: str
    marker_value: str
    heading: str
    parts: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    page_nos: list[int] = field(default_factory=list)
    refs: list[str] = field(default_factory=list)

    def append(self, chunk_text: str, *, headings: list[str], page_nos: list[int], refs: list[str]) -> None:
        if chunk_text.strip():
            self.parts.append(chunk_text.strip())
        for heading in headings:
            if heading and heading not in self.headings:
                self.headings.append(heading)
        for page_no in page_nos:
            if page_no not in self.page_nos:
                self.page_nos.append(page_no)
        for ref in refs:
            if ref and ref not in self.refs:
                self.refs.append(ref)

    def build_text(self) -> str:
        return "\n\n".join(part for part in self.parts if part).strip()


def chunk_tender_document(
    document: ParsedDocument,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    if document.docling_document is None:
        raise ValueError("ParsedDocument.docling_document is required for tender chunking")

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

    hierarchical_chunker = HierarchicalChunker()
    raw_chunks = list(hierarchical_chunker.chunk(document.docling_document))
    if not raw_chunks:
        return []

    candidates = _merge_tender_chunks(raw_chunks)
    return _finalize_candidates(
        document=document,
        candidates=candidates,
        chunk_size=resolved_chunk_size,
        chunk_overlap=resolved_chunk_overlap,
    )


def _merge_tender_chunks(raw_chunks) -> list[TenderChunkCandidate]:
    candidates: list[TenderChunkCandidate] = []
    current: TenderChunkCandidate | None = None

    for raw_chunk in raw_chunks:
        chunk_text = raw_chunk.text.strip()
        if not chunk_text:
            continue

        headings = [heading for heading in (raw_chunk.meta.headings or []) if heading]
        page_nos = _extract_page_nos(raw_chunk)
        refs = _extract_refs(raw_chunk)
        marker = _detect_marker(chunk_text, headings)

        if marker is not None:
            current = TenderChunkCandidate(
                marker_type=marker["type"],
                marker_value=marker["value"],
                heading=marker["heading"],
            )
            current.append(chunk_text, headings=headings, page_nos=page_nos, refs=refs)
            candidates.append(current)
            continue

        if current is None:
            current = TenderChunkCandidate(
                marker_type="unclassified",
                marker_value="unclassified",
                heading=headings[-1] if headings else chunk_text.splitlines()[0].strip(),
            )
            candidates.append(current)

        current.append(chunk_text, headings=headings, page_nos=page_nos, refs=refs)

    return candidates


def _finalize_candidates(
    *,
    document: ParsedDocument,
    candidates: list[TenderChunkCandidate],
    chunk_size: int,
    chunk_overlap: int,
) -> list[DocumentChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks: list[DocumentChunk] = []

    for candidate in candidates:
        candidate_text = candidate.build_text()
        if not candidate_text:
            continue

        split_texts = _split_candidate_text(
            candidate_text,
            heading=candidate.heading,
            marker_type=candidate.marker_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter=splitter,
        )
        for text in split_texts:
            chunk_index = len(chunks)
            chunk_id = str(uuid5(NAMESPACE_URL, f"{document.doc_id}:tender:{chunk_index}:{text}"))
            metadata = {
                "chunker": "tender",
                "marker_type": candidate.marker_type,
                "marker_value": candidate.marker_value,
                "heading": candidate.heading,
                "page_nos": sorted(candidate.page_nos),
                "doc_refs": candidate.refs,
            }
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    doc_id=document.doc_id,
                    source=document.source,
                    index=chunk_index,
                    markdown=text,
                    text=markdown_to_text(text),
                    headers=candidate.headings or [candidate.heading],
                    metadata=metadata,
                )
            )

    return chunks


def _split_candidate_text(
    text: str,
    *,
    heading: str,
    marker_type: str,
    chunk_size: int,
    chunk_overlap: int,
    splitter: RecursiveCharacterTextSplitter,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []

    protected_prefix = []
    remaining_lines = lines
    if marker_type in {"catalog", "subitem"} and len(lines) > 1:
        protected_prefix = [lines[0]]
        if len(lines) > 1 and SPECIAL_RE.match(lines[1].strip()):
            protected_prefix.append(lines[1])
            remaining_lines = lines[2:]
        else:
            remaining_lines = lines[1:]

    prefix_text = "\n".join(protected_prefix).strip()
    body_text = "\n".join(remaining_lines).strip()
    if not body_text:
        return [text]

    body_chunk_size = max(200, chunk_size - len(prefix_text) - 2) if prefix_text else chunk_size
    body_chunk_overlap = min(chunk_overlap, max(0, body_chunk_size // 4))
    body_splitter = splitter
    if body_chunk_size != chunk_size or body_chunk_overlap != chunk_overlap:
        body_splitter = RecursiveCharacterTextSplitter(
            chunk_size=body_chunk_size,
            chunk_overlap=body_chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

    body_chunks = [chunk.strip() for chunk in body_splitter.split_text(body_text) if chunk.strip()]
    if not prefix_text:
        return body_chunks

    return [
        f"{prefix_text}\n\n{chunk}".strip()
        for chunk in body_chunks
    ]


def _detect_marker(chunk_text: str, headings: list[str]) -> dict | None:
    text = chunk_text.strip()
    first_line = text.splitlines()[0].strip() if text else ""
    candidates = [first_line, *(reversed(headings))]

    for candidate in candidates:
        marker = _match_marker(candidate)
        if marker is not None:
            return marker
    return None


def _match_marker(text: str) -> dict | None:
    if not text:
        return None
    if CHAPTER_RE.match(text):
        return {"type": "chapter", "value": text, "heading": text}
    if SECTION_RE.match(text):
        return {"type": "section", "value": text, "heading": text}
    if CLAUSE_RE.match(text):
        value = text.split()[0]
        return {"type": "clause", "value": value, "heading": text}
    if (match := CATALOG_PREFIX_RE.match(text)) is not None:
        return {"type": "catalog", "value": match.group(1), "heading": text}
    if SUBITEM_RE.match(text):
        return {"type": "subitem", "value": text, "heading": text}
    if SPECIAL_RE.match(text):
        return {"type": "special", "value": text, "heading": text}
    return None


def _extract_page_nos(raw_chunk) -> list[int]:
    page_nos: list[int] = []
    for item in raw_chunk.meta.doc_items:
        prov = getattr(item, "prov", None)
        prov_list = prov if isinstance(prov, list) else [prov] if prov is not None else []
        if not prov_list:
            continue
        first_prov = prov_list[0]
        page_no = getattr(first_prov, "page_no", None)
        if isinstance(page_no, int) and page_no not in page_nos:
            page_nos.append(page_no)
    return page_nos


def _extract_refs(raw_chunk) -> list[str]:
    refs: list[str] = []
    for item in raw_chunk.meta.doc_items:
        ref = getattr(item, "self_ref", None)
        if isinstance(ref, str) and ref not in refs:
            refs.append(ref)
    return refs
