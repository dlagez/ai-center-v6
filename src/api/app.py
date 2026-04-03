from fastapi import FastAPI

from src.api.routes import router
from src.config.settings import settings

app = FastAPI(title=settings.app_name)
app.include_router(router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}
