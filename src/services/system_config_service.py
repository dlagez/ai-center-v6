from src.db.models.system_config import SystemConfig
from src.repositories.system_config_repository import SystemConfigRepository


class SystemConfigService:
    def __init__(self, repository: SystemConfigRepository) -> None:
        self.repository = repository

    def create_config(self, key: str, value: str) -> SystemConfig:
        if self.repository.get_by_key(key):
            raise ValueError(f"System config already exists: {key}")
        return self.repository.create(key=key, value=value)

    def get_config(self, config_id: int) -> SystemConfig:
        entity = self.repository.get_by_id(config_id)
        if entity is None:
            raise ValueError(f"System config not found: {config_id}")
        return entity

    def list_configs(self) -> list[SystemConfig]:
        return self.repository.list_all()

    def update_config(self, config_id: int, value: str) -> SystemConfig:
        entity = self.repository.get_by_id(config_id)
        if entity is None:
            raise ValueError(f"System config not found: {config_id}")
        return self.repository.update_value(entity=entity, value=value)

    def delete_config(self, config_id: int) -> None:
        entity = self.repository.get_by_id(config_id)
        if entity is None:
            raise ValueError(f"System config not found: {config_id}")
        self.repository.delete(entity)
