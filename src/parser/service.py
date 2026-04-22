import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from src.db.models.docling_parse_result import DoclingParseResult
from src.parser.parser import DoclingBlockPreview, DoclingPagePreview, DoclingParser
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.uploaded_file_service import UploadedFileService
from src.storage.file_service import get_file_service


class DoclingParseServiceResult:
    def __init__(
        self,
        *,
        file_id: str,
        file_name: str,
        status: str,
        error: str | None = None,
        summary: dict | None = None,
        pages: list[DoclingPagePreview] | None = None,
        blocks: list[DoclingBlockPreview] | None = None,
        result: dict | None = None,
    ) -> None:
        self.file_id = file_id
        self.file_name = file_name
        self.status = status
        self.error = error
        self.summary = summary or {}
        self.pages = pages or []
        self.blocks = blocks or []
        self.result = result


class DoclingParserService:
    def __init__(
        self,
        uploaded_file_repository: UploadedFileRepository,
        docling_parse_result_repository: DoclingParseResultRepository,
        parser: DoclingParser | None = None,
    ) -> None:
        self.uploaded_file_service = UploadedFileService(uploaded_file_repository)
        self.docling_parse_result_repository = docling_parse_result_repository
        self.parser = parser or DoclingParser()

    def parse_pdf_file(self, file_id: str) -> DoclingParseServiceResult:
        file_record = self.uploaded_file_service.get_pdf_file(file_id)
        cached = self.docling_parse_result_repository.get_by_file_id(file_id)
        if cached and cached.parse_status == "success" and cached.result_json:
            return self._build_cached_response(file_record.file_id, file_record.file_name, cached)

        temp_path = None
        try:
            payload = get_file_service().download_file(file_record.object_name)
            suffix = Path(file_record.file_name).suffix or ".pdf"
            temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(payload)
            temp_file.flush()
            temp_file.close()
            temp_path = temp_file.name

            parsed_document = self.parser.parse(temp_path)
            parsed = self.parser.parse_visualized_pdf(temp_path)
            page_count = parsed["summary"].get("total_pages", 0)

            cached = self._ensure_cache_entity(cached, file_id)
            cached.parse_status = "success"
            cached.error_message = None
            cached.result_json = json.dumps(parsed["result"], ensure_ascii=False)
            cached.markdown = parsed_document.markdown
            cached.page_count = page_count
            self._save_cache(cached)

            return DoclingParseServiceResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="success",
                summary=parsed["summary"],
                pages=parsed["pages"],
                blocks=parsed["blocks"],
                result=parsed["result"],
            )
        except Exception as exc:
            cached = self._ensure_cache_entity(cached, file_id)
            cached.parse_status = "failed"
            cached.error_message = str(exc)
            cached.result_json = None
            cached.markdown = None
            cached.page_count = 0
            self._save_cache(cached)
            return DoclingParseServiceResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="failed",
                error=str(exc),
            )
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

    def _build_cached_response(
        self,
        file_id: str,
        file_name: str,
        cached: DoclingParseResult,
    ) -> DoclingParseServiceResult:
        result = json.loads(cached.result_json or "{}")
        visualized = self.parser.build_visualized_payload_from_dict(result)
        return DoclingParseServiceResult(
            file_id=file_id,
            file_name=file_name,
            status="success",
            summary=visualized["summary"],
            pages=visualized["pages"],
            blocks=visualized["blocks"],
            result=visualized["result"],
        )

    @staticmethod
    def _ensure_cache_entity(
        cached: DoclingParseResult | None,
        file_id: str,
    ) -> DoclingParseResult:
        if cached is not None:
            return cached
        return DoclingParseResult(
            parse_id=uuid4().hex,
            file_id=file_id,
            parser_name="docling",
            parser_version="docling_visual_v1",
        )

    def _save_cache(self, cached: DoclingParseResult) -> None:
        if cached.id:
            self.docling_parse_result_repository.update(cached)
        else:
            self.docling_parse_result_repository.create(cached)
