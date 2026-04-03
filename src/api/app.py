from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes import router
from src.config.settings import settings
from src.observability import flush_langfuse


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        flush_langfuse()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
