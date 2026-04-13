from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

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
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
