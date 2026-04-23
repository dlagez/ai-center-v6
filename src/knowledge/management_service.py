from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from qdrant_client import models

from src.chunker import chunk_document, chunk_tender_document
from src.db.models.knowledge_base import KnowledgeBase
from src.db.models.knowledge_document import KnowledgeDocument
from src.knowledge.schemas import SearchResult
from src.knowledge.store import QdrantStore
from src.models.embeddings import embed_query, embed_texts
from src.parser.parser import DoclingParser
from src.parser.service import DoclingParserService
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
from src.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository


class KnowledgeManagementService:
    def __init__(
        self,
        uploaded_file_repository: UploadedFileRepository,
        docling_parse_task_repository: DoclingParseTaskRepository,
        docling_parse_result_repository: DoclingParseResultRepository,
        knowledge_base_repository: KnowledgeBaseRepository,
        knowledge_document_repository: KnowledgeDocumentRepository,
        parser: DoclingParser | None = None,
    ) -> None:
        self.uploaded_file_repository = uploaded_file_repository
        self.knowledge_base_repository = knowledge_base_repository
        self.knowledge_document_repository = knowledge_document_repository
        self.parser = parser or DoclingParser()
        self.parser_service = DoclingParserService(
            uploaded_file_repository,
            docling_parse_task_repository,
            docling_parse_result_repository,
            parser=self.parser,
        )

    def list_bases(self, *, limit: int = 200) -> list[dict[str, Any]]:
        bases = self.knowledge_base_repository.list_all(limit=limit)
        return [self._serialize_base(base) for base in bases]

    def create_base(
        self,
        *,
        name: str,
        description: str | None = None,
        biz_type: str = "general",
        chunker_type: str = "default",
        embedding_model: str | None = None,
        created_by: str | None = None,
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Knowledge base name must not be empty")
        if chunker_type not in {"default", "tender"}:
            raise ValueError(f"Unsupported chunker_type: {chunker_type}")

        kb_id = uuid4().hex
        collection_name = f"kb_{kb_id}"
        if self.knowledge_base_repository.get_by_collection_name(collection_name):
            raise ValueError("Knowledge base collection already exists")

        store = self._get_store(collection_name)
        store.ensure_collection()

        entity = KnowledgeBase(
            kb_id=kb_id,
            name=normalized_name,
            description=description.strip() if description else None,
            biz_type=biz_type.strip() or "general",
            embedding_model=embedding_model.strip() if embedding_model else None,
            chunker_type=chunker_type,
            qdrant_collection=collection_name,
            status="active",
            created_by=created_by,
        )
        return self._serialize_base(self.knowledge_base_repository.create(entity))

    def update_base(
        self,
        kb_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        biz_type: str | None = None,
        chunker_type: str | None = None,
        embedding_model: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        base = self._get_base_entity(kb_id)
        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("Knowledge base name must not be empty")
            base.name = normalized_name
        if description is not None:
            base.description = description.strip() or None
        if biz_type is not None:
            base.biz_type = biz_type.strip() or "general"
        if chunker_type is not None:
            if chunker_type not in {"default", "tender"}:
                raise ValueError(f"Unsupported chunker_type: {chunker_type}")
            base.chunker_type = chunker_type
        if embedding_model is not None:
            base.embedding_model = embedding_model.strip() or None
        if status is not None:
            base.status = status.strip() or base.status
        return self._serialize_base(self.knowledge_base_repository.update(base))

    def delete_base(self, kb_id: str) -> dict[str, str]:
        base = self._get_base_entity(kb_id)
        store = self._get_store(base.qdrant_collection)
        store.client.delete_collection(collection_name=base.qdrant_collection)
        self.knowledge_document_repository.delete_by_kb_id(kb_id)
        self.knowledge_base_repository.delete(base)
        return {"kb_id": kb_id, "collection_name": base.qdrant_collection}

    def get_base_stats(self, kb_id: str) -> dict[str, Any]:
        base = self._get_base_entity(kb_id)
        return self._serialize_base(base)

    def list_documents(self, kb_id: str, *, limit: int = 500) -> list[dict[str, Any]]:
        base = self._get_base_entity(kb_id)
        documents = self.knowledge_document_repository.list_by_kb_id(base.kb_id, limit=limit)
        documents = [self._reconcile_document_state(item) for item in documents]
        return [self._serialize_document(item) for item in documents]

    def index_file(
        self,
        kb_id: str,
        file_id: str,
        *,
        chunker_type: str | None = None,
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        base = self._get_base_entity(kb_id)
        file_record = self._get_file_record(file_id)
        resolved_chunker = chunker_type or base.chunker_type
        document = self._prepare_index_record(
            kb_id=base.kb_id,
            file_record=file_record,
            chunker_type=resolved_chunker,
        )
        self._set_document_stage(
            document,
            stage="parsing",
            status="running",
            parse_task_id=self._extract_parse_task_id(file_record.file_id),
        )

        parse_result = self.parser_service.parse_pdf_file(file_id)
        if parse_result.status != "success" or parse_result.docling_document is None:
            self._mark_document_failed(
                document,
                stage="parsing",
                parse_task_id=self._extract_parse_task_id(file_record.file_id),
                page_count=len(parse_result.pages),
                error_message=parse_result.error or "Docling parse failed",
            )
            self._refresh_base_counters(base.kb_id)
            raise ValueError(parse_result.error or "Docling parse failed")

        parse_task_id = self._extract_parse_task_id(file_record.file_id)
        self._set_document_stage(
            document,
            stage="parsed",
            status="running",
            parse_task_id=parse_task_id,
            page_count=len(parse_result.pages),
        )

        try:
            self._set_document_stage(
                document,
                stage="chunking",
                status="running",
                parse_task_id=parse_task_id,
                page_count=len(parse_result.pages),
            )
            parsed_document = self.parser.build_parsed_document(
                parse_result.docling_document,
                source=file_record.object_name,
            )
            chunks = self._build_chunks(parsed_document, resolved_chunker)
            sample_heading = self._extract_sample_heading(chunks)
            self._set_document_stage(
                document,
                stage="embedding",
                status="running",
                parse_task_id=parse_task_id,
                page_count=len(parse_result.pages),
                chunk_count=len(chunks),
                sample_heading=sample_heading,
            )
            vectors = embed_texts(
                [chunk.text for chunk in chunks],
                model=embedding_model or base.embedding_model,
            )

            self._delete_qdrant_document(base.qdrant_collection, file_id, chunker_type=resolved_chunker)

            store = self._get_store(base.qdrant_collection)
            store.ensure_collection()
            self._set_document_stage(
                document,
                stage="indexing",
                status="running",
                parse_task_id=parse_task_id,
                page_count=len(parse_result.pages),
                chunk_count=len(chunks),
                sample_heading=sample_heading,
            )
            points = [
                models.PointStruct(
                    id=chunk.id,
                    vector=vector,
                    payload={
                        "doc_id": chunk.doc_id,
                        "source": chunk.source,
                        "index": chunk.index,
                        "text": chunk.text,
                        "markdown": chunk.markdown,
                        "headers": chunk.headers,
                        "metadata": {
                            **chunk.metadata,
                            "kb_id": base.kb_id,
                            "kb_name": base.name,
                            "file_id": file_record.file_id,
                            "file_name": file_record.file_name,
                            "folder_path": file_record.folder_path,
                            "chunker": resolved_chunker,
                        },
                    },
                )
                for chunk, vector in zip(chunks, vectors, strict=True)
            ]
            if points:
                store.client.upsert(collection_name=store.collection_name, points=points)
        except Exception as exc:
            self._mark_document_failed(
                document,
                stage=document.current_stage,
                parse_task_id=parse_task_id,
                page_count=len(parse_result.pages),
                chunk_count=document.chunk_count,
                sample_heading=document.sample_heading or "",
                error_message=str(exc),
            )
            self._refresh_base_counters(base.kb_id)
            raise

        self._mark_document_success(
            document,
            parse_task_id=parse_task_id,
            chunk_count=len(chunks),
            page_count=len(parse_result.pages),
            sample_heading=sample_heading,
        )

        self._refresh_base_counters(base.kb_id)
        base = self._get_base_entity(base.kb_id)
        return {
            "kb_id": base.kb_id,
            "kb_name": base.name,
            "file_id": file_record.file_id,
            "file_name": file_record.file_name,
            "chunker": resolved_chunker,
            "chunk_count": len(chunks),
            "collection_name": base.qdrant_collection,
            "page_count": len(parse_result.pages),
            "parse_status": parse_result.status,
        }

    def delete_document(
        self,
        kb_id: str,
        file_id: str,
        *,
        chunker_type: str | None = None,
    ) -> dict[str, str]:
        base = self._get_base_entity(kb_id)
        self._delete_qdrant_document(base.qdrant_collection, file_id, chunker_type=chunker_type)

        document = self.knowledge_document_repository.get_by_kb_id_and_file_id(
            kb_id,
            file_id,
            chunker_type=chunker_type,
        )
        if document is not None:
            self.knowledge_document_repository.delete(document)
            self._refresh_base_counters(kb_id)

        return {"kb_id": kb_id, "file_id": file_id, "chunker": chunker_type or "all"}

    def _delete_qdrant_document(
        self,
        collection_name: str,
        file_id: str,
        *,
        chunker_type: str | None = None,
    ) -> None:
        store = self._get_store(collection_name)
        must_conditions = [
            models.FieldCondition(
                key="metadata.file_id",
                match=models.MatchValue(value=file_id),
            ),
        ]
        if chunker_type:
            must_conditions.append(
                models.FieldCondition(
                    key="metadata.chunker",
                    match=models.MatchValue(value=chunker_type),
                )
            )
        store.client.delete(
            collection_name=store.collection_name,
            points_selector=models.FilterSelector(filter=models.Filter(must=must_conditions)),
        )

    def search(
        self,
        kb_id: str,
        *,
        query: str,
        file_id: str | None = None,
        chunker_type: str | None = None,
        limit: int = 5,
        embedding_model: str | None = None,
    ) -> dict[str, Any]:
        base = self._get_base_entity(kb_id)
        query_text = query.strip()
        if not query_text:
            raise ValueError("Query must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        query_vector = embed_query(query_text, model=embedding_model or base.embedding_model)
        must_conditions: list[models.Condition] = []
        if file_id:
            must_conditions.append(
                models.FieldCondition(
                    key="metadata.file_id",
                    match=models.MatchValue(value=file_id),
                )
            )
        if chunker_type:
            must_conditions.append(
                models.FieldCondition(
                    key="metadata.chunker",
                    match=models.MatchValue(value=chunker_type),
                )
            )
        query_filter = models.Filter(must=must_conditions) if must_conditions else None

        store = self._get_store(base.qdrant_collection)
        points = store.client.query_points(
            collection_name=store.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=query_filter,
        ).points

        results = [
            SearchResult(
                id=str(point.id),
                doc_id=str(point.payload.get("doc_id", "")),
                source=str(point.payload.get("source", "")),
                index=int(point.payload.get("index", 0)),
                text=str(point.payload.get("text", "")),
                score=float(point.score),
                headers=list(point.payload.get("headers", [])),
                metadata=dict(point.payload.get("metadata", {})),
            )
            for point in points
        ]
        return {
            "kb_id": base.kb_id,
            "kb_name": base.name,
            "query": query_text,
            "limit": limit,
            "collection_name": base.qdrant_collection,
            "results": results,
        }

    def _build_chunks(self, parsed_document, chunker_type: str):
        if chunker_type == "tender":
            return chunk_tender_document(parsed_document)
        if chunker_type == "default":
            return chunk_document(parsed_document)
        raise ValueError(f"Unsupported chunker_type: {chunker_type}")

    def _get_base_entity(self, kb_id: str) -> KnowledgeBase:
        base = self.knowledge_base_repository.get_by_kb_id(kb_id)
        if base is None:
            raise ValueError(f"Knowledge base not found: {kb_id}")
        return base

    def _get_file_record(self, file_id: str):
        file_record = self.uploaded_file_repository.get_by_file_id(file_id)
        if file_record is None:
            raise ValueError(f"File not found: {file_id}")
        return file_record

    def _refresh_base_counters(self, kb_id: str) -> None:
        base = self._get_base_entity(kb_id)
        documents = self.knowledge_document_repository.list_by_kb_id(kb_id, limit=5000)
        base.document_count = len(documents)
        base.chunk_count = sum(item.chunk_count for item in documents)
        self.knowledge_base_repository.update(base)

    def _serialize_base(self, base: KnowledgeBase) -> dict[str, Any]:
        return {
            "kb_id": base.kb_id,
            "name": base.name,
            "description": base.description or "",
            "biz_type": base.biz_type,
            "embedding_model": base.embedding_model or "",
            "chunker_type": base.chunker_type,
            "collection_name": base.qdrant_collection,
            "status": base.status,
            "document_count": base.document_count,
            "chunk_count": base.chunk_count,
            "created_by": base.created_by or "",
            "created_at": base.created_at.isoformat() if base.created_at else "",
            "updated_at": base.updated_at.isoformat() if base.updated_at else "",
        }

    def _serialize_document(self, document: KnowledgeDocument) -> dict[str, Any]:
        return {
            "kb_id": document.kb_id,
            "file_id": document.file_id,
            "file_name": document.file_name,
            "parse_task_id": document.parse_task_id or "",
            "chunker": document.chunker_type,
            "status": document.status,
            "retry_count": document.retry_count,
            "current_stage": document.current_stage,
            "last_error_stage": document.last_error_stage or "",
            "chunk_count": document.chunk_count,
            "page_count": document.page_count,
            "sample_heading": document.sample_heading or "",
            "folder_path": document.folder_path or "",
            "error_message": document.error_message or "",
            "last_index_started_at": document.last_index_started_at.isoformat() if document.last_index_started_at else "",
            "last_index_finished_at": document.last_index_finished_at.isoformat() if document.last_index_finished_at else "",
            "last_retry_at": document.last_retry_at.isoformat() if document.last_retry_at else "",
            "indexed_at": document.indexed_at.isoformat() if document.indexed_at else "",
            "created_at": document.created_at.isoformat() if document.created_at else "",
            "updated_at": document.updated_at.isoformat() if document.updated_at else "",
        }

    def _reconcile_document_state(self, document: KnowledgeDocument) -> KnowledgeDocument:
        if document.status != "running":
            return document
        if document.last_index_finished_at is not None:
            return document
        if document.last_index_started_at is None:
            return document

        stale_threshold = datetime.now() - timedelta(minutes=5)
        if document.last_index_started_at > stale_threshold:
            return document

        parse_task = None
        if document.parse_task_id:
            parse_task = self.parser_service.docling_parse_task_repository.get_by_task_id(document.parse_task_id)

        if parse_task and parse_task.status in {"running", "pending"}:
            return document

        if document.current_stage == "parsing" and parse_task and parse_task.status == "success":
            error_message = "Indexing request was interrupted after parsing completed. Retry will reuse cached parse results."
        else:
            error_message = "Indexing request was interrupted before completion. Please retry."

        document.status = "failed"
        document.last_error_stage = document.current_stage
        document.error_message = error_message
        document.last_index_finished_at = datetime.now()
        return self.knowledge_document_repository.update(document)

    def _extract_parse_task_id(self, file_id: str) -> str | None:
        task = self.parser_service.docling_parse_task_repository.get_latest_by_file_id(file_id)
        if task is None:
            return None
        return task.task_id

    def _prepare_index_record(
        self,
        *,
        kb_id: str,
        file_record,
        chunker_type: str,
    ) -> KnowledgeDocument:
        document = self.knowledge_document_repository.get_by_kb_id_and_file_id(
            kb_id,
            file_record.file_id,
            chunker_type=chunker_type,
        )
        now = datetime.now()
        if document is None:
            document = KnowledgeDocument(
                kb_id=kb_id,
                file_id=file_record.file_id,
                file_name=file_record.file_name,
                parse_task_id=None,
                chunker_type=chunker_type,
                status="pending",
                chunk_count=0,
                page_count=0,
                sample_heading=None,
                folder_path=file_record.folder_path,
                retry_count=0,
                current_stage="pending",
                last_error_stage=None,
                error_message=None,
                last_index_started_at=now,
                last_index_finished_at=None,
                last_retry_at=None,
                indexed_at=None,
            )
            return self.knowledge_document_repository.create(document)

        if document.status == "failed":
            document.retry_count += 1
            document.last_retry_at = now
        document.file_name = file_record.file_name
        document.folder_path = file_record.folder_path
        document.last_index_started_at = now
        document.last_index_finished_at = None
        document.indexed_at = None
        document.last_error_stage = None
        document.error_message = None
        return self.knowledge_document_repository.update(document)

    def _set_document_stage(
        self,
        document: KnowledgeDocument,
        *,
        stage: str,
        status: str,
        parse_task_id: str | None,
        page_count: int | None = None,
        chunk_count: int | None = None,
        sample_heading: str | None = None,
    ) -> KnowledgeDocument:
        document.parse_task_id = parse_task_id
        document.current_stage = stage
        document.status = status
        if page_count is not None:
            document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if sample_heading is not None:
            document.sample_heading = sample_heading or None
        document.last_error_stage = None
        document.error_message = None
        return self.knowledge_document_repository.update(document)

    def _mark_document_failed(
        self,
        document: KnowledgeDocument,
        *,
        stage: str,
        parse_task_id: str | None,
        page_count: int,
        error_message: str,
        chunk_count: int | None = None,
        sample_heading: str | None = None,
    ) -> KnowledgeDocument:
        document.parse_task_id = parse_task_id
        document.status = "failed"
        document.current_stage = stage
        document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        if sample_heading is not None:
            document.sample_heading = sample_heading or None
        document.last_error_stage = stage
        document.error_message = error_message
        document.last_index_finished_at = datetime.now()
        return self.knowledge_document_repository.update(document)

    def _mark_document_success(
        self,
        document: KnowledgeDocument,
        *,
        parse_task_id: str | None,
        chunk_count: int,
        page_count: int,
        sample_heading: str,
    ) -> KnowledgeDocument:
        document.parse_task_id = parse_task_id
        document.status = "active"
        document.current_stage = "indexed"
        document.chunk_count = chunk_count
        document.page_count = page_count
        document.sample_heading = sample_heading or None
        document.last_error_stage = None
        document.error_message = None
        now = datetime.now()
        document.last_index_finished_at = now
        document.indexed_at = now
        return self.knowledge_document_repository.update(document)

    def _extract_sample_heading(self, chunks: Iterable) -> str:
        for chunk in chunks:
            heading = str(chunk.metadata.get("heading", "")).strip()
            if heading:
                return heading
            if chunk.headers:
                return str(chunk.headers[-1]).strip()
        return ""

    def _get_store(self, collection_name: str) -> QdrantStore:
        return QdrantStore(collection_name=collection_name)
