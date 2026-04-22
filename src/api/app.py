from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.pdf_preview_routes import router as pdf_preview_router
from src.api.routes import router
from src.config.settings import settings
from src.db.session import init_db
from src.observability import flush_langfuse
from src.storage.minio_client import ensure_minio_bucket


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        init_db()
        ensure_minio_bucket()
        yield
    finally:
        flush_langfuse()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
app.include_router(pdf_preview_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
