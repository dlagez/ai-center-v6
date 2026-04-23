from datetime import datetime
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from src.db.models.docling_parse_result import DoclingParseResult
from src.db.models.docling_parse_task import DoclingParseTask
from src.parser.parser import DoclingParser
from src.parser.utils import (
    DoclingBlockPreview,
    DoclingPagePreview,
    build_parsed_document,
    build_visualized_payload,
)
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
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
        docling_document=None,
        result: dict | None = None,
    ) -> None:
        self.file_id = file_id
        self.file_name = file_name
        self.status = status
        self.error = error
        self.summary = summary or {}
        self.pages = pages or []
        self.blocks = blocks or []
        self.docling_document = docling_document
        self.result = result


class DoclingParseTaskSummary:
    def __init__(
        self,
        *,
        task_id: str,
        file_id: str,
        file_name: str,
        status: str,
        progress: float,
        total_pages: int,
        parsed_pages: int,
        failed_pages: int,
        batch_size: int,
        current_batch_no: int,
        parser_version: str,
        error_message: str | None,
        started_at,
        finished_at,
        created_at,
        updated_at,
    ) -> None:
        self.task_id = task_id
        self.file_id = file_id
        self.file_name = file_name
        self.status = status
        self.progress = progress
        self.total_pages = total_pages
        self.parsed_pages = parsed_pages
        self.failed_pages = failed_pages
        self.batch_size = batch_size
        self.current_batch_no = current_batch_no
        self.parser_version = parser_version
        self.error_message = error_message
        self.started_at = started_at
        self.finished_at = finished_at
        self.created_at = created_at
        self.updated_at = updated_at


class DoclingParseTaskDetail(DoclingParseTaskSummary):
    def __init__(
        self,
        *,
        failed_results: list[dict],
        page_results: list[dict],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.failed_results = failed_results
        self.page_results = page_results


class DoclingParserService:
    batch_size = 10

    def __init__(
        self,
        uploaded_file_repository: UploadedFileRepository,
        docling_parse_task_repository: DoclingParseTaskRepository,
        docling_parse_result_repository: DoclingParseResultRepository,
        parser: DoclingParser | None = None,
    ) -> None:
        self.uploaded_file_service = UploadedFileService(uploaded_file_repository)
        self.docling_parse_task_repository = docling_parse_task_repository
        self.docling_parse_result_repository = docling_parse_result_repository
        self.parser = parser or DoclingParser()

    def parse_pdf_file(self, file_id: str) -> DoclingParseServiceResult:
        file_record = self.uploaded_file_service.get_pdf_file(file_id)
        cached_response = self._load_cached_response(file_record.file_id, file_record.file_name)
        if cached_response is not None:
            return cached_response

        temp_path = None
        task = None
        try:
            task = self._start_task(file_id)
            temp_path = self._download_to_temp_path(file_record.object_name, file_record.file_name)
            batch_results, batch_page_entities, last_batch_no = self._parse_batches(
                file_id=file_id,
                task=task,
                temp_path=temp_path,
            )
            if not batch_page_entities:
                raise ValueError("Docling did not return any parsed pages")

            self.docling_parse_result_repository.create_many(batch_page_entities)
            return self._finalize_success(
                task=task,
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                batch_results=batch_results,
                batch_page_entities=batch_page_entities,
                last_batch_no=last_batch_no,
            )
        except Exception as exc:
            if task is None:
                task = self._ensure_task_entity(file_id)
            task.status = "failed"
            task.error_message = str(exc)
            task.finished_at = datetime.now()
            self._save_task(task)
            return DoclingParseServiceResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="failed",
                error=str(exc),
            )
        finally:
            if temp_path:
                Path(temp_path).unlink(missing_ok=True)

    def list_tasks(self, *, file_id: str | None = None, limit: int = 50) -> list[DoclingParseTaskSummary]:
        tasks = self.docling_parse_task_repository.list_recent(file_id=file_id, limit=limit)
        file_names = self._resolve_file_names(tasks)
        return [
            self._build_task_summary(task, file_names.get(task.file_id, task.file_id))
            for task in tasks
        ]

    def get_task_detail(self, task_id: str) -> DoclingParseTaskDetail:
        task = self.docling_parse_task_repository.get_by_task_id(task_id)
        if task is None:
            raise ValueError("Parse task not found")

        file_record = self.uploaded_file_service.get_pdf_file(task.file_id)
        page_results = self.docling_parse_result_repository.list_by_task_id(task_id)
        failed_results = self.docling_parse_result_repository.list_failed_by_task_id(task_id)

        return DoclingParseTaskDetail(
            **self._build_task_summary(task, file_record.file_name).__dict__,
            failed_results=[
                {
                    "page_no": item.page_no,
                    "batch_no": item.batch_no,
                    "error_message": item.error_message,
                    "parse_status": item.parse_status,
                }
                for item in failed_results
            ],
            page_results=[
                {
                    "page_no": item.page_no,
                    "batch_no": item.batch_no,
                    "parse_status": item.parse_status,
                    "block_count": item.block_count,
                    "updated_at": item.updated_at,
                }
                for item in page_results
            ],
        )

    def _build_cached_response(
        self,
        file_id: str,
        file_name: str,
        cached_results: list[DoclingParseResult],
    ) -> DoclingParseServiceResult:
        page_docs = [
            self.parser.deserialize_doc(json.loads(item.result_json or "{}"))
            for item in cached_results
            if item.result_json
        ]
        merged_docling_document = self.parser.concatenate_docs(page_docs)
        merged_result = merged_docling_document.export_to_dict()
        visualized = build_visualized_payload(merged_docling_document)
        return DoclingParseServiceResult(
            file_id=file_id,
            file_name=file_name,
            status="success",
            summary=visualized["summary"],
            pages=visualized["pages"],
            blocks=visualized["blocks"],
            docling_document=merged_docling_document,
            result=merged_result,
        )

    def _load_cached_response(
        self,
        file_id: str,
        file_name: str,
    ) -> DoclingParseServiceResult | None:
        task = self.docling_parse_task_repository.get_latest_by_file_id(file_id)
        if task is None or task.status not in {"success", "partial_success"}:
            return None
        cached_results = self.docling_parse_result_repository.list_by_task_id(task.task_id)
        if not cached_results or not all(item.result_json for item in cached_results):
            return None
        return self._build_cached_response(file_id, file_name, cached_results)

    @staticmethod
    def _ensure_task_entity(file_id: str) -> DoclingParseTask:
        return DoclingParseTask(
            task_id=uuid4().hex,
            file_id=file_id,
            parser_name="docling",
            parser_version="docling_visual_v1",
        )

    def _save_task(self, task: DoclingParseTask) -> None:
        if task.id:
            self.docling_parse_task_repository.update(task)
        else:
            self.docling_parse_task_repository.create(task)

    def _start_task(self, file_id: str) -> DoclingParseTask:
        task = self._ensure_task_entity(file_id)
        task.status = "running"
        task.error_message = None
        task.started_at = task.started_at or datetime.now()
        task.batch_size = self.batch_size
        self._save_task(task)
        return task

    @staticmethod
    def _download_to_temp_path(object_name: str, file_name: str) -> str:
        payload = get_file_service().download_file(object_name)
        suffix = Path(file_name).suffix or ".pdf"
        temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(payload)
        temp_file.flush()
        temp_file.close()
        return temp_file.name

    def _parse_batches(
        self,
        *,
        file_id: str,
        task: DoclingParseTask,
        temp_path: str,
    ) -> tuple[list, list[DoclingParseResult], int]:
        batch_docs: list = []
        batch_page_entities: list[DoclingParseResult] = []
        start_page = 1
        batch_no = 1

        while True:
            batch_doc, batch_entities = self._parse_single_batch(
                file_id=file_id,
                task=task,
                temp_path=temp_path,
                start_page=start_page,
                batch_no=batch_no,
            )
            if batch_doc is None or not batch_entities:
                break

            batch_docs.append(batch_doc)
            batch_page_entities.extend(batch_entities)
            max_page_no = max(item.page_no for item in batch_entities)

            task.current_batch_no = batch_no
            task.total_pages = max(task.total_pages, max_page_no)
            task.parsed_pages = len(batch_page_entities)
            task.progress = 0.00
            self._save_task(task)

            if len(batch_entities) < self.batch_size:
                break

            start_page = max_page_no + 1
            batch_no += 1

        return batch_docs, batch_page_entities, batch_no

    def _parse_single_batch(
        self,
        *,
        file_id: str,
        task: DoclingParseTask,
        temp_path: str,
        start_page: int,
        batch_no: int,
    ) -> tuple[object | None, list[DoclingParseResult]]:
        end_page = start_page + self.batch_size - 1
        page_range = (start_page, end_page)
        docling_document = self.parser.parse(
            temp_path,
            page_range=page_range,
            enable_page_images=True,
        )
        parsed_document = build_parsed_document(docling_document, source=temp_path)
        parsed = build_visualized_payload(docling_document)
        parsed_pages = parsed.get("pages", [])
        if not parsed_pages:
            return None, []

        batch_entities = self._build_page_results(
            task=task,
            file_id=file_id,
            parsed=parsed,
            markdown=parsed_document.markdown,
            docling_document_dict=docling_document.export_to_dict(),
            batch_no=batch_no,
        )
        return docling_document, batch_entities

    def _finalize_success(
        self,
        *,
        task: DoclingParseTask,
        file_id: str,
        file_name: str,
        batch_results: list,
        batch_page_entities: list[DoclingParseResult],
        last_batch_no: int,
    ) -> DoclingParseServiceResult:
        task.total_pages = max(item.page_no for item in batch_page_entities)
        task.parsed_pages = len(batch_page_entities)
        task.failed_pages = 0
        task.progress = 100.00
        task.current_batch_no = last_batch_no
        task.status = "success"
        task.finished_at = datetime.now()
        self._save_task(task)

        merged_docling_document = self.parser.concatenate_docs(batch_results)
        merged_result = merged_docling_document.export_to_dict()
        visualized = build_visualized_payload(merged_docling_document)
        return DoclingParseServiceResult(
            file_id=file_id,
            file_name=file_name,
            status="success",
            summary=visualized["summary"],
            pages=visualized["pages"],
            blocks=visualized["blocks"],
            docling_document=merged_docling_document,
            result=merged_result,
        )

    def _resolve_file_names(self, tasks: list[DoclingParseTask]) -> dict[str, str]:
        file_names: dict[str, str] = {}
        for task in tasks:
            if task.file_id in file_names:
                continue
            try:
                file_record = self.uploaded_file_service.get_pdf_file(task.file_id)
                file_names[task.file_id] = file_record.file_name
            except ValueError:
                file_names[task.file_id] = task.file_id
        return file_names

    @staticmethod
    def _build_task_summary(task: DoclingParseTask, file_name: str) -> DoclingParseTaskSummary:
        progress = float(task.progress) if task.progress is not None else 0.0
        return DoclingParseTaskSummary(
            task_id=task.task_id,
            file_id=task.file_id,
            file_name=file_name,
            status=task.status,
            progress=progress,
            total_pages=task.total_pages,
            parsed_pages=task.parsed_pages,
            failed_pages=task.failed_pages,
            batch_size=task.batch_size,
            current_batch_no=task.current_batch_no,
            parser_version=task.parser_version,
            error_message=task.error_message,
            started_at=task.started_at,
            finished_at=task.finished_at,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )

    @staticmethod
    def _build_page_results(
        task: DoclingParseTask,
        file_id: str,
        parsed: dict,
        markdown: str,
        docling_document_dict: dict | None,
        batch_no: int,
    ) -> list[DoclingParseResult]:
        blocks = parsed.get("blocks", [])
        pages = parsed.get("pages", [])
        raw_result = parsed.get("result") or {}
        page_markdowns = markdown.split("\f") if markdown else []
        entities: list[DoclingParseResult] = []

        for index, page in enumerate(pages):
            page_no = page.page_no
            page_blocks = [block for block in blocks if block.page_no == page_no]
            page_payload = _build_page_doc_payload(docling_document_dict or raw_result, page_no=page_no)
            page_markdown = page_markdowns[index] if index < len(page_markdowns) else None
            entities.append(
                DoclingParseResult(
                    result_id=uuid4().hex,
                    task_id=task.task_id,
                    file_id=file_id,
                    batch_no=batch_no,
                    page_no=page_no,
                    parser_name=task.parser_name,
                    parser_version=task.parser_version,
                    parse_status="success",
                    error_message=None,
                    result_json=json.dumps(page_payload, ensure_ascii=False),
                    markdown=page_markdown,
                    block_count=len(page_blocks),
                )
            )

        return entities

    @staticmethod
    def _merge_page_results(results: list[DoclingParseResult]) -> dict:
        merged_doc: dict = {}

        for item in results:
            payload = json.loads(item.result_json or "{}")
            merged_doc = _merge_doc_dicts(merged_doc, payload)

        return merged_doc

    @staticmethod
    def _merge_visualized_batches(batches: list[dict]) -> dict:
        merged_doc: dict = {}

        for batch in batches:
            raw_result = batch.get("result") or {}
            merged_doc = _merge_doc_dicts(merged_doc, raw_result)

        return merged_doc



def _item_matches_page(item: dict, page_no: int) -> bool:
    prov = item.get("prov")
    if prov is None:
        return False
    prov_list = prov if isinstance(prov, list) else [prov]
    if not prov_list:
        return False
    first_prov = prov_list[0] or {}
    return first_prov.get("page_no") == page_no and first_prov.get("bbox") is not None


def _build_page_doc_payload(doc_dict: dict, *, page_no: int) -> dict:
    return {
        "schema_name": doc_dict.get("schema_name", "DoclingDocument"),
        "version": doc_dict.get("version"),
        "name": doc_dict.get("name", "Document"),
        "origin": doc_dict.get("origin"),
        "furniture": doc_dict.get("furniture"),
        "body": doc_dict.get("body"),
        "groups": [item for item in doc_dict.get("groups", []) if _item_matches_page(item, page_no)],
        "texts": [item for item in doc_dict.get("texts", []) if _item_matches_page(item, page_no)],
        "pictures": [item for item in doc_dict.get("pictures", []) if _item_matches_page(item, page_no)],
        "tables": [item for item in doc_dict.get("tables", []) if _item_matches_page(item, page_no)],
        "key_value_items": [
            item for item in doc_dict.get("key_value_items", []) if _item_matches_page(item, page_no)
        ],
        "form_items": [item for item in doc_dict.get("form_items", []) if _item_matches_page(item, page_no)],
        "field_regions": [
            item for item in doc_dict.get("field_regions", []) if _item_matches_page(item, page_no)
        ],
        "field_items": [item for item in doc_dict.get("field_items", []) if _item_matches_page(item, page_no)],
        "pages": {str(page_no): doc_dict.get("pages", {}).get(str(page_no), {})},
    }


def _merge_doc_dicts(base: dict, addition: dict) -> dict:
    if not base:
        return {
            "schema_name": addition.get("schema_name", "DoclingDocument"),
            "version": addition.get("version"),
            "name": addition.get("name", "Document"),
            "origin": addition.get("origin"),
            "furniture": addition.get("furniture"),
            "body": addition.get("body"),
            "groups": list(addition.get("groups", [])),
            "texts": list(addition.get("texts", [])),
            "pictures": list(addition.get("pictures", [])),
            "tables": list(addition.get("tables", [])),
            "key_value_items": list(addition.get("key_value_items", [])),
            "form_items": list(addition.get("form_items", [])),
            "field_regions": list(addition.get("field_regions", [])),
            "field_items": list(addition.get("field_items", [])),
            "pages": dict(addition.get("pages", {})),
        }

    merged = dict(base)
    for key in [
        "groups",
        "texts",
        "pictures",
        "tables",
        "key_value_items",
        "form_items",
        "field_regions",
        "field_items",
    ]:
        merged[key] = list(merged.get(key, [])) + list(addition.get(key, []))

    merged["pages"] = dict(merged.get("pages", {}))
    merged["pages"].update(addition.get("pages", {}))
    return merged
