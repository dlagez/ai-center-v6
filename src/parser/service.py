from datetime import datetime
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from src.db.models.docling_parse_result import DoclingParseResult
from src.db.models.docling_parse_task import DoclingParseTask
from src.parser.parser import DoclingBlockPreview, DoclingPagePreview, DoclingParser
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
        task = self.docling_parse_task_repository.get_latest_by_file_id(file_id)
        if task and task.status in {"success", "partial_success"}:
            cached_results = self.docling_parse_result_repository.list_by_task_id(task.task_id)
            if cached_results and all(item.result_json for item in cached_results):
                return self._build_cached_response(file_record.file_id, file_record.file_name, cached_results)

        temp_path = None
        task = None
        try:
            task = self._ensure_task_entity(file_id)
            task.status = "running"
            task.error_message = None
            task.started_at = task.started_at or datetime.now()
            task.batch_size = self.batch_size
            self._save_task(task)

            payload = get_file_service().download_file(file_record.object_name)
            suffix = Path(file_record.file_name).suffix or ".pdf"
            temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(payload)
            temp_file.flush()
            temp_file.close()
            temp_path = temp_file.name

            batch_results: list[dict] = []
            batch_page_entities: list[DoclingParseResult] = []
            start_page = 1
            batch_no = 1

            while True:
                end_page = start_page + self.batch_size - 1
                page_range = (start_page, end_page)
                parsed_document = self.parser.parse(temp_path, page_range=page_range)
                parsed = self.parser.parse_visualized_pdf(temp_path, page_range=page_range)
                parsed_pages = parsed.get("pages", [])
                if not parsed_pages:
                    break

                batch_results.append(parsed)
                batch_page_entities.extend(
                    self._build_page_results(
                        task=task,
                        file_id=file_id,
                        parsed=parsed,
                        markdown=parsed_document.markdown,
                        batch_no=batch_no,
                    )
                )

                max_page_no = max(page.page_no for page in parsed_pages)
                task.current_batch_no = batch_no
                task.total_pages = max(task.total_pages, max_page_no)
                task.parsed_pages = len(batch_page_entities)
                task.progress = 0.00
                self._save_task(task)

                if len(parsed_pages) < self.batch_size:
                    break

                start_page = max_page_no + 1
                batch_no += 1

            if not batch_page_entities:
                raise ValueError("Docling did not return any parsed pages")

            self.docling_parse_result_repository.create_many(batch_page_entities)

            task.total_pages = max(item.page_no for item in batch_page_entities)
            task.parsed_pages = len(batch_page_entities)
            task.failed_pages = 0
            task.progress = 100.00
            task.current_batch_no = batch_no
            task.status = "success"
            task.finished_at = datetime.now()
            self._save_task(task)

            merged_result = self._merge_visualized_batches(batch_results)
            visualized = self.parser.build_visualized_payload_from_dict(merged_result)
            return DoclingParseServiceResult(
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                status="success",
                summary=visualized["summary"],
                pages=visualized["pages"],
                blocks=visualized["blocks"],
                result=merged_result,
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
        merged_result = self._merge_page_results(cached_results)
        visualized = self.parser.build_visualized_payload_from_dict(merged_result)
        return DoclingParseServiceResult(
            file_id=file_id,
            file_name=file_name,
            status="success",
            summary=visualized["summary"],
            pages=visualized["pages"],
            blocks=visualized["blocks"],
            result=merged_result,
        )

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
        batch_no: int,
    ) -> list[DoclingParseResult]:
        blocks = parsed.get("blocks", [])
        pages = parsed.get("pages", [])
        raw_result = parsed.get("result") or {}
        raw_pages = raw_result.get("pages") or {}
        page_markdowns = markdown.split("\f") if markdown else []
        entities: list[DoclingParseResult] = []

        for index, page in enumerate(pages):
            page_no = page.page_no
            page_blocks = [block for block in blocks if block.page_no == page_no]
            page_nodes = _collect_raw_nodes_for_page(raw_result, page_no)
            page_payload = {
                "pages": {str(page_no): raw_pages.get(str(page_no), {})},
                "key_value_items": [],
                "body": None,
                "furniture": None,
                "groups": [],
                "page_nodes": page_nodes,
            }
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
        merged_pages: dict[str, dict] = {}
        merged_blocks: list[dict] = []

        for item in results:
            payload = json.loads(item.result_json or "{}")
            pages = payload.get("pages") or {}
            merged_pages.update(pages)
            merged_blocks.extend(payload.get("page_nodes") or [])

        return {
            "pages": merged_pages,
            "key_value_items": [],
            "body": None,
            "furniture": None,
            "groups": [],
            "page_nodes": merged_blocks,
        }

    @staticmethod
    def _merge_visualized_batches(batches: list[dict]) -> dict:
        merged_pages: dict[str, dict] = {}
        merged_nodes: list[dict] = []

        for batch in batches:
            raw_result = batch.get("result") or {}
            merged_pages.update(raw_result.get("pages") or {})
            merged_nodes.extend(_collect_raw_nodes_for_pages(raw_result))

        return {
            "pages": merged_pages,
            "key_value_items": [],
            "body": None,
            "furniture": None,
            "groups": [],
            "page_nodes": merged_nodes,
        }


def _collect_raw_nodes_for_page(payload, page_no: int) -> list[dict]:
    nodes: list[dict] = []

    if isinstance(payload, dict):
        prov_list = payload.get("prov")
        if not isinstance(prov_list, list) and prov_list is not None:
            prov_list = [prov_list]

        if prov_list:
            first_prov = prov_list[0] or {}
            if first_prov.get("page_no") == page_no and first_prov.get("bbox") is not None:
                nodes.append(payload)

        for value in payload.values():
            nodes.extend(_collect_raw_nodes_for_page(value, page_no))
    elif isinstance(payload, list):
        for value in payload:
            nodes.extend(_collect_raw_nodes_for_page(value, page_no))

    return nodes


def _collect_raw_nodes_for_pages(payload) -> list[dict]:
    nodes: list[dict] = []

    if isinstance(payload, dict):
        prov_list = payload.get("prov")
        if not isinstance(prov_list, list) and prov_list is not None:
            prov_list = [prov_list]

        if prov_list:
            first_prov = prov_list[0] or {}
            if first_prov.get("page_no") is not None and first_prov.get("bbox") is not None:
                nodes.append(payload)

        for value in payload.values():
            nodes.extend(_collect_raw_nodes_for_pages(value))
    elif isinstance(payload, list):
        for value in payload:
            nodes.extend(_collect_raw_nodes_for_pages(value))

    return nodes
