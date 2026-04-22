from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings
from src.db.base import Base


def _build_engine() -> Engine:
    if not settings.database_url:
        raise ValueError("DATABASE_URL must be configured")
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
    )


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, autocommit=False, class_=Session)


def get_engine() -> Engine:
    global engine
    if engine is None:
        engine = _build_engine()
        SessionLocal.configure(bind=engine)
    return engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from src.db.models import docling_parse_result  # noqa: F401
    from src.db.models import docling_parse_task  # noqa: F401
    from src.db.models import system_config  # noqa: F401
    from src.db.models import uploaded_file  # noqa: F401
    from src.workflow.excel_update import models as excel_update_models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
