from fastapi import APIRouter, HTTPException

from src.api.schemas import IngestRequest
from src.knowledge.service import KnowledgeIngestionService

router = APIRouter()


@router.post("/knowledge/ingest")
async def ingest_knowledge(request: IngestRequest) -> dict:
    service = KnowledgeIngestionService()

    try:
        result = service.ingest_path(source=request.source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Knowledge ingestion failed: {exc}") from exc

    return result.model_dump()
