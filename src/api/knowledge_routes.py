from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.schemas import PdfPreviewFileResponse
from src.db.session import get_db
from src.knowledge.management_service import KnowledgeManagementService
from src.knowledge.schemas import SearchResult
from src.repositories.docling_parse_result_repository import DoclingParseResultRepository
from src.repositories.docling_parse_task_repository import DoclingParseTaskRepository
from src.repositories.knowledge_base_repository import KnowledgeBaseRepository
from src.repositories.knowledge_document_repository import KnowledgeDocumentRepository
from src.repositories.uploaded_file_repository import UploadedFileRepository
from src.services.uploaded_file_service import UploadedFileService

router = APIRouter()


class KnowledgeBaseResponse(BaseModel):
    kb_id: str
    name: str
    description: str
    biz_type: str
    embedding_model: str
    chunker_type: str
    collection_name: str
    status: str
    document_count: int
    chunk_count: int
    created_by: str
    created_at: str
    updated_at: str


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    biz_type: str = Field(default="general", min_length=1, max_length=64)
    chunker_type: str = Field(default="default")
    embedding_model: str | None = None
    created_by: str | None = None


class KnowledgeBaseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    biz_type: str | None = Field(default=None, min_length=1, max_length=64)
    chunker_type: str | None = None
    embedding_model: str | None = None
    status: str | None = None


class KnowledgeDocumentResponse(BaseModel):
    kb_id: str
    file_id: str
    file_name: str
    parse_task_id: str
    chunker: str
    status: str
    chunk_count: int
    page_count: int
    sample_heading: str
    folder_path: str
    error_message: str
    created_at: str
    updated_at: str


class KnowledgeIndexRequest(BaseModel):
    file_id: str
    chunker_type: str | None = None


class KnowledgeIndexResponse(BaseModel):
    kb_id: str
    kb_name: str
    file_id: str
    file_name: str
    chunker: str
    chunk_count: int
    collection_name: str
    page_count: int
    parse_status: str


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    file_id: str | None = None
    chunker_type: str | None = None
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResponse(BaseModel):
    kb_id: str
    kb_name: str
    query: str
    limit: int
    collection_name: str
    results: list[SearchResult]


class KnowledgeDeleteResponse(BaseModel):
    kb_id: str
    file_id: str
    chunker: str


class KnowledgeBaseDeleteResponse(BaseModel):
    kb_id: str
    collection_name: str


def _build_service(db: Session) -> KnowledgeManagementService:
    return KnowledgeManagementService(
        UploadedFileRepository(db),
        DoclingParseTaskRepository(db),
        DoclingParseResultRepository(db),
        KnowledgeBaseRepository(db),
        KnowledgeDocumentRepository(db),
    )


@router.get("/api/knowledge/bases", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(db: Session = Depends(get_db)) -> list[KnowledgeBaseResponse]:
    service = _build_service(db)
    return [KnowledgeBaseResponse(**item) for item in service.list_bases()]


@router.post("/api/knowledge/bases", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreateRequest,
    db: Session = Depends(get_db),
) -> KnowledgeBaseResponse:
    service = _build_service(db)
    try:
        result = service.create_base(
            name=request.name,
            description=request.description,
            biz_type=request.biz_type,
            chunker_type=request.chunker_type,
            embedding_model=request.embedding_model,
            created_by=request.created_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeBaseResponse(**result)


@router.patch("/api/knowledge/bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    request: KnowledgeBaseUpdateRequest,
    db: Session = Depends(get_db),
) -> KnowledgeBaseResponse:
    service = _build_service(db)
    try:
        result = service.update_base(
            kb_id,
            name=request.name,
            description=request.description,
            biz_type=request.biz_type,
            chunker_type=request.chunker_type,
            embedding_model=request.embedding_model,
            status=request.status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeBaseResponse(**result)


@router.delete("/api/knowledge/bases/{kb_id}", response_model=KnowledgeBaseDeleteResponse)
async def delete_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeBaseDeleteResponse:
    service = _build_service(db)
    try:
        result = service.delete_base(kb_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return KnowledgeBaseDeleteResponse(**result)


@router.get("/api/knowledge/bases/{kb_id}/stats", response_model=KnowledgeBaseResponse)
async def get_knowledge_base_stats(
    kb_id: str,
    db: Session = Depends(get_db),
) -> KnowledgeBaseResponse:
    service = _build_service(db)
    try:
        result = service.get_base_stats(kb_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return KnowledgeBaseResponse(**result)


@router.get("/api/knowledge/bases/{kb_id}/documents", response_model=list[KnowledgeDocumentResponse])
async def list_knowledge_documents(
    kb_id: str,
    limit: int = 500,
    db: Session = Depends(get_db),
) -> list[KnowledgeDocumentResponse]:
    service = _build_service(db)
    try:
        result = service.list_documents(kb_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [KnowledgeDocumentResponse(**item) for item in result]


@router.get("/api/knowledge/files", response_model=list[PdfPreviewFileResponse])
async def list_knowledge_files(db: Session = Depends(get_db)) -> list[PdfPreviewFileResponse]:
    service = UploadedFileService(UploadedFileRepository(db))
    return service.list_pdf_files()


@router.post("/api/knowledge/bases/{kb_id}/documents/index", response_model=KnowledgeIndexResponse)
async def index_knowledge_document(
    kb_id: str,
    request: KnowledgeIndexRequest,
    db: Session = Depends(get_db),
) -> KnowledgeIndexResponse:
    service = _build_service(db)
    try:
        result = service.index_file(kb_id, request.file_id, chunker_type=request.chunker_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeIndexResponse(**result)


@router.delete("/api/knowledge/bases/{kb_id}/documents/{file_id}", response_model=KnowledgeDeleteResponse)
async def delete_knowledge_document(
    kb_id: str,
    file_id: str,
    chunker_type: str | None = None,
    db: Session = Depends(get_db),
) -> KnowledgeDeleteResponse:
    service = _build_service(db)
    try:
        result = service.delete_document(kb_id, file_id, chunker_type=chunker_type)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return KnowledgeDeleteResponse(**result)


@router.post("/api/knowledge/bases/{kb_id}/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    kb_id: str,
    request: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
) -> KnowledgeSearchResponse:
    service = _build_service(db)
    try:
        result = service.search(
            kb_id,
            query=request.query,
            file_id=request.file_id,
            chunker_type=request.chunker_type,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KnowledgeSearchResponse(**result)
