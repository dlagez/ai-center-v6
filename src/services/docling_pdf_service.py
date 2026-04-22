from pathlib import Path
from tempfile import NamedTemporaryFile

from src.knowledge.parser import (
    DoclingBlockPreview,
    DoclingPagePreview,
    DoclingParser,
)
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.uploaded_file_service import UploadedFileService
from src.storage.file_service import get_file_service


class DoclingPdfParseResult:
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


class DoclingPdfService:
    def __init__(
        self,
        uploaded_file_repository: UploadedFileRepository,
        parser: DoclingParser | None = None,
    ) -> None:
        self.uploaded_file_service = UploadedFileService(uploaded_file_repository)
        self.parser = parser or DoclingParser()

    def parse_uploaded_pdf(self, file_id: str) -> DoclingPdfParseResult:
        file_record = self.uploaded_file_service.get_pdf_file(file_id)

        temp_path = None
        try:
            payload = get_file_service().download_file(file_record.object_name)
            suffix = Path(file_record.file_name).suffix or ".pdf"
            temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(payload)
            temp_file.flush()
            temp_file.close()
            temp_path = temp_file.name

            parsed = self.parser.parse_visualized_pdf(temp_path)
            return DoclingPdfParseResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="success",
                summary=parsed["summary"],
                pages=parsed["pages"],
                blocks=parsed["blocks"],
                result=parsed["result"],
            )
        except Exception as exc:
            return DoclingPdfParseResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="failed",
                error=str(exc),
            )
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)
