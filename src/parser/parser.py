import base64
import io
import re
from hashlib import sha1
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter
from docling.document_converter import PdfFormatOption
from pydantic import BaseModel

from src.knowledge.schemas import ParsedDocument


def markdown_to_text(markdown: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>~]", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class DoclingParser:
    def __init__(self) -> None:
        self.converter = DocumentConverter()
        visual_options = PdfPipelineOptions(
            do_ocr=False,
            generate_page_images=True,
        )
        self.visual_converter = DocumentConverter(
            allowed_formats=[InputFormat.PDF],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=visual_options),
            },
        )

    def parse(self, source: str | Path) -> ParsedDocument:
        result = self.converter.convert(source)
        doc = result.document
        markdown = doc.export_to_markdown()
        source_str = str(source)

        return ParsedDocument(
            doc_id=sha1(source_str.encode("utf-8")).hexdigest(),
            source=source_str,
            markdown=markdown,
            text=markdown_to_text(markdown),
            metadata={"source_type": "docling"},
        )

    def parse_visualized_pdf(self, source: str | Path) -> dict:
        result = self.visual_converter.convert(source)
        doc = result.document
        doc_dict = doc.export_to_dict()
        return self.build_visualized_payload_from_dict(doc_dict, doc=doc)

    def build_visualized_payload_from_dict(self, doc_dict: dict, doc=None) -> dict:
        raw_pages = doc_dict.get("pages") or {}

        blocks: list[DoclingBlockPreview] = []
        block_counts: dict[int, int] = {}
        for raw_path, node in _collect_blocks(doc_dict):
            page_no, bbox, coord_origin = _extract_page_no_and_bbox(node)
            page_item = raw_pages.get(str(page_no)) if page_no is not None else None
            bbox_norm = _normalize_bbox(bbox, page_item, coord_origin)
            block = DoclingBlockPreview(
                page_no=page_no,
                label=str(node.get("label") or node.get("type") or ""),
                text_preview=_extract_text_preview(node),
                bbox=bbox,
                bbox_norm=bbox_norm,
                coord_origin=coord_origin,
                self_ref=_normalize_ref(node.get("self_ref")),
                parent=_normalize_ref(node.get("parent")),
                raw_path=raw_path,
            )
            blocks.append(block)
            if page_no is not None:
                block_counts[page_no] = block_counts.get(page_no, 0) + 1

        return {
            "summary": _build_summary(doc_dict, blocks),
            "pages": _build_page_previews(doc_dict, block_counts, doc),
            "blocks": sorted(blocks, key=_block_sort_key),
            "result": doc_dict,
        }


class DoclingPagePreview(BaseModel):
    page_no: int
    image_data_url: str | None = None
    block_count: int


class DoclingBlockPreview(BaseModel):
    page_no: int | None
    label: str
    text_preview: str
    bbox: list[float] | None
    bbox_norm: list[float] | None
    coord_origin: str | None = None
    self_ref: str | None
    parent: str | None
    raw_path: str


def _ensure_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_page_no_and_bbox(node: dict) -> tuple[int | None, list[float] | None, str | None]:
    prov_list = _ensure_list(node.get("prov"))
    if not prov_list:
        return None, None, None

    first_prov = prov_list[0] or {}
    page_no = first_prov.get("page_no")
    bbox = first_prov.get("bbox")
    coord_origin = None

    if isinstance(bbox, dict):
        left = bbox.get("l")
        top = bbox.get("t")
        right = bbox.get("r")
        bottom = bbox.get("b")
        coord_origin = bbox.get("coord_origin")
        if all(value is not None for value in [left, top, right, bottom]):
            return page_no, [float(left), float(top), float(right), float(bottom)], coord_origin

    if isinstance(bbox, list) and len(bbox) >= 4:
        return page_no, [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])], coord_origin

    return page_no, None, coord_origin


def _extract_text_preview(node: dict) -> str:
    for key in ["text", "orig", "raw_text", "name", "captions"]:
        value = node.get(key)
        if isinstance(value, str):
            return value[:80]
        if isinstance(value, list) and value and isinstance(value[0], str):
            return value[0][:80]
    return ""


def _normalize_ref(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        ref_value = value.get("$ref")
        if isinstance(ref_value, str):
            return ref_value
        return str(value)
    return str(value)


def _normalize_bbox(
    bbox: list[float] | None,
    page_item: dict | None,
    coord_origin: str | None,
) -> list[float] | None:
    if bbox is None or page_item is None:
        return None

    size = page_item.get("size") or {}
    width = size.get("width")
    height = size.get("height")
    if not width or not height:
        return None

    left, top, right, bottom = bbox
    normalized_origin = (coord_origin or "").upper()

    if normalized_origin == "BOTTOMLEFT":
        top, bottom = height - bottom, height - top

    x0 = max(0.0, min(1.0, left / width))
    y0 = max(0.0, min(1.0, top / height))
    x1 = max(0.0, min(1.0, right / width))
    y1 = max(0.0, min(1.0, bottom / height))
    x_min, x_max = sorted([x0, x1])
    y_min, y_max = sorted([y0, y1])
    return [x_min, y_min, x_max, y_max]


def _collect_blocks(payload, *, path: str = "root") -> list[tuple[str, dict]]:
    blocks: list[tuple[str, dict]] = []

    if isinstance(payload, dict):
        prov_list = _ensure_list(payload.get("prov"))
        has_page_prov = False
        if prov_list:
            first_prov = prov_list[0] or {}
            has_page_prov = first_prov.get("page_no") is not None and first_prov.get("bbox") is not None

        if has_page_prov:
            blocks.append((path, payload))

        for key, value in payload.items():
            blocks.extend(_collect_blocks(value, path=f"{path}.{key}"))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            blocks.extend(_collect_blocks(value, path=f"{path}[{index}]"))

    return blocks


def _build_summary(doc_dict: dict, blocks: list[DoclingBlockPreview]) -> dict:
    pages = doc_dict.get("pages") or {}
    labels = [block.label for block in blocks]
    return {
        "total_pages": len(pages),
        "text_blocks": sum(
            1
            for label in labels
            if label in {"text", "paragraph", "title", "section_header", "page_header", "page_footer"}
        ),
        "table_blocks": sum(1 for label in labels if label == "table"),
        "picture_blocks": sum(1 for label in labels if label == "picture"),
        "key_value_items": len(doc_dict.get("key_value_items") or []),
        "body_exists": bool(doc_dict.get("body")),
        "furniture_exists": bool(doc_dict.get("furniture")),
        "groups_exists": bool(doc_dict.get("groups")),
    }


def _block_sort_key(block: DoclingBlockPreview) -> tuple:
    page_no = block.page_no or 0
    if block.bbox_norm and len(block.bbox_norm) == 4:
        x0, y0, x1, y1 = block.bbox_norm
        return (page_no, y0, x0, y1 - y0, x1 - x0, block.label, block.raw_path)
    return (page_no, 999.0, 999.0, 999.0, 999.0, block.label, block.raw_path)


def _build_page_previews(doc_dict: dict, block_counts: dict[int, int], doc) -> list[DoclingPagePreview]:
    pages: list[DoclingPagePreview] = []
    raw_pages = doc_dict.get("pages") or {}

    for page_no in sorted(raw_pages.keys(), key=int):
        image_data_url = None
        page_item = doc.pages.get(int(page_no)) if doc is not None and hasattr(doc, "pages") else None
        page_image = getattr(page_item, "image", None)
        pil_image = None
        if page_image is not None and hasattr(page_image, "pil_image"):
            pil_image = page_image.pil_image
        if pil_image is not None:
            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            image_data_url = f"data:image/png;base64,{encoded}"

        pages.append(
            DoclingPagePreview(
                page_no=int(page_no),
                image_data_url=image_data_url,
                block_count=block_counts.get(int(page_no), 0),
            )
        )

    return pages
