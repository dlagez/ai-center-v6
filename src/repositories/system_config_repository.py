from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.system_config import SystemConfig


class SystemConfigRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, key: str, value: str) -> SystemConfig:
        entity = SystemConfig(key=key, value=value)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def get_by_id(self, config_id: int) -> SystemConfig | None:
        statement = select(SystemConfig).where(SystemConfig.id == config_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_key(self, key: str) -> SystemConfig | None:
        statement = select(SystemConfig).where(SystemConfig.key == key)
        return self.db.execute(statement).scalar_one_or_none()

    def list_all(self) -> list[SystemConfig]:
        statement = select(SystemConfig).order_by(SystemConfig.id.asc())
        return list(self.db.execute(statement).scalars().all())

    def update_value(self, entity: SystemConfig, value: str) -> SystemConfig:
        entity.value = value
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: SystemConfig) -> None:
        self.db.delete(entity)
        self.db.commit()
