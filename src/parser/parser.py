from pathlib import Path
from typing import Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.settings import PageRange
from docling.document_converter import DocumentConverter
from docling.document_converter import PdfFormatOption
from docling_core.types.doc import DoclingDocument


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

    def parse(
        self,
        source: str | Path,
        page_range: PageRange | None = None,
        *,
        enable_page_images: bool = False,
    ) -> DoclingDocument:
        convert_kwargs: dict[str, Any] = {}
        if page_range is not None:
            convert_kwargs["page_range"] = page_range
        converter = self.visual_converter if enable_page_images else self.converter
        result = converter.convert(source, **convert_kwargs)
        doc_dict = result.document.export_to_dict()
        normalized = _normalize_doc_dict_page_numbers(doc_dict, page_range)
        return self.deserialize_doc(normalized["doc_dict"])

    @staticmethod
    def deserialize_doc(doc_dict: dict) -> DoclingDocument:
        return DoclingDocument.model_validate(doc_dict)

    @staticmethod
    def concatenate_docs(docs: list[DoclingDocument]) -> DoclingDocument:
        if not docs:
            raise ValueError("At least one DoclingDocument is required")
        if len(docs) == 1:
            return docs[0]
        return DoclingDocument.concatenate(docs)


def _normalize_doc_dict_page_numbers(
    doc_dict: dict,
    page_range: PageRange | None,
) -> dict[str, Any]:
    if page_range is None:
        return {"doc_dict": doc_dict, "page_number_map": {}}

    if isinstance(page_range, tuple):
        start_page = int(page_range[0])
    else:
        start_page = int(getattr(page_range, "start", 1) or 1)

    if start_page <= 1:
        return {"doc_dict": doc_dict, "page_number_map": {}}

    normalized = dict(doc_dict)
    normalized_pages: dict[str, Any] = {}
    page_number_map: dict[int, int] = {}

    for key, value in (doc_dict.get("pages") or {}).items():
        try:
            original_page_no = int(key)
        except (TypeError, ValueError):
            normalized_pages[str(key)] = value
            continue

        normalized_page_no = original_page_no + start_page - 1
        page_number_map[original_page_no] = normalized_page_no

        page_payload = dict(value) if isinstance(value, dict) else value
        if isinstance(page_payload, dict):
            page_payload["page_no"] = normalized_page_no
        normalized_pages[str(normalized_page_no)] = page_payload

    normalized["pages"] = normalized_pages
    if page_number_map:
        _shift_page_numbers(normalized, start_page - 1)
    return {"doc_dict": normalized, "page_number_map": page_number_map}


def _shift_page_numbers(payload, offset: int):
    if offset == 0:
        return payload

    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "page_no" and isinstance(value, int):
                payload[key] = value + offset
            elif key == "pages" and isinstance(value, dict):
                continue
            else:
                _shift_page_numbers(value, offset)
    elif isinstance(payload, list):
        for item in payload:
            _shift_page_numbers(item, offset)

    return payload
