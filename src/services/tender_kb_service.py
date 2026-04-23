from typing import Any

from qdrant_client import models

from src.chunker import chunk_tender_document
from src.knowledge.store import QdrantStore
from src.models.embeddings import embed_query, embed_texts
from src.models.llm import chat_completion
from src.parser.parser import DoclingParser
from src.parser.service import DoclingParserService
from src.parser.utils import build_parsed_document
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository


class TenderKbService:
    def __init__(
        self,
        uploaded_file_repository: UploadedFileRepository,
        docling_parse_task_repository: DoclingParseTaskRepository,
        docling_parse_result_repository: DoclingParseResultRepository,
        parser: DoclingParser | None = None,
        store: QdrantStore | None = None,
    ) -> None:
        self.uploaded_file_repository = uploaded_file_repository
        self.parser = parser or DoclingParser()
        self.parser_service = DoclingParserService(
            uploaded_file_repository,
            docling_parse_task_repository,
            docling_parse_result_repository,
            parser=self.parser,
        )
        self.store = store or QdrantStore()
        self.store.ensure_collection()

    def index_file(self, file_id: str, *, embedding_model: str | None = None) -> dict[str, Any]:
        file_record = self._get_file_record(file_id)
        parse_result = self.parser_service.parse_pdf_file(file_id)
        if parse_result.status != "success" or parse_result.docling_document is None:
            raise ValueError(parse_result.error or "Docling parse failed")

        parsed_document = build_parsed_document(
            parse_result.docling_document,
            source=file_record.object_name,
        )
        chunks = chunk_tender_document(parsed_document)
        vectors = embed_texts([chunk.text for chunk in chunks], model=embedding_model)

        self._delete_existing_chunks(file_id)
        self._upsert_chunks(file_record, chunks, vectors)

        return {
            "file_id": file_record.file_id,
            "file_name": file_record.file_name,
            "parse_status": parse_result.status,
            "chunk_count": len(chunks),
            "collection_name": self.store.collection_name,
            "pages": len(parse_result.pages),
        }

    def ask(
        self,
        *,
        file_id: str,
        question: str,
        limit: int = 5,
        embedding_model: str | None = None,
        llm_model: str | None = None,
    ) -> dict[str, Any]:
        query_text = question.strip()
        if not query_text:
            raise ValueError("Question must not be empty")
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        file_record = self._get_file_record(file_id)
        query_vector = embed_query(query_text, model=embedding_model)
        result = self.store.client.query_points(
            collection_name=self.store.collection_name,
            query=query_vector,
            limit=limit,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.file_id",
                        match=models.MatchValue(value=file_id),
                    ),
                    models.FieldCondition(
                        key="metadata.chunker",
                        match=models.MatchValue(value="tender"),
                    ),
                ]
            ),
        )
        points = result.points
        sources = [
            {
                "id": str(point.id),
                "score": float(point.score),
                "text": str(point.payload.get("text", "")),
                "headers": list(point.payload.get("headers", [])),
                "metadata": dict(point.payload.get("metadata", {})),
            }
            for point in points
        ]

        answer = self._generate_answer(
            file_name=file_record.file_name,
            question=query_text,
            sources=sources,
            llm_model=llm_model,
        )
        return {
            "file_id": file_record.file_id,
            "file_name": file_record.file_name,
            "question": query_text,
            "answer": answer,
            "sources": sources,
        }

    def _generate_answer(
        self,
        *,
        file_name: str,
        question: str,
        sources: list[dict[str, Any]],
        llm_model: str | None,
    ) -> str:
        if not sources:
            return "当前知识库中没有检索到相关内容。"

        context_blocks = []
        for index, source in enumerate(sources, start=1):
            metadata = source.get("metadata", {})
            context_blocks.append(
                "\n".join(
                    [
                        f"[片段{index}]",
                        f"标题: {metadata.get('heading') or ''}",
                        f"目录项类型: {metadata.get('marker_type') or ''}",
                        f"页码: {metadata.get('page_nos') or []}",
                        f"内容: {source.get('text') or ''}",
                    ]
                )
            )

        prompt = "\n\n".join(
            [
                f"你正在回答招投标/资格预审文件相关问题，文件名：{file_name}。",
                "请严格基于给定片段作答，不要编造未出现的信息。",
                "如果片段不足以回答，请明确说“依据当前入库内容无法确定”。",
                f"问题：{question}",
                "参考片段：",
                "\n\n".join(context_blocks),
            ]
        )

        return chat_completion(
            messages=[
                {"role": "system", "content": "你是一个严谨的招投标文件知识库问答助手。"},
                {"role": "user", "content": prompt},
            ],
            model=llm_model,
        )

    def _upsert_chunks(self, file_record, chunks, vectors) -> None:
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
                        "file_id": file_record.file_id,
                        "file_name": file_record.file_name,
                        "folder_path": file_record.folder_path,
                    },
                },
            )
            for chunk, vector in zip(chunks, vectors)
        ]
        if not points:
            return
        self.store.client.upsert(
            collection_name=self.store.collection_name,
            points=points,
        )

    def _delete_existing_chunks(self, file_id: str) -> None:
        self.store.client.delete(
            collection_name=self.store.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.file_id",
                            match=models.MatchValue(value=file_id),
                        ),
                        models.FieldCondition(
                            key="metadata.chunker",
                            match=models.MatchValue(value="tender"),
                        ),
                    ]
                )
            ),
        )

    def _get_file_record(self, file_id: str):
        file_record = self.uploaded_file_repository.get_by_file_id(file_id)
        if file_record is None or file_record.status != "active" or file_record.content_type != "application/pdf":
            raise ValueError("PDF file not found")
        return file_record
