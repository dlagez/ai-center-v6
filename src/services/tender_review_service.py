from uuid import uuid4

from src.db.models.tender_review_item import TenderReviewItem
from src.db.models.tender_review_task import TenderReviewTask
from src.repositories.tender_review_item_repository import TenderReviewItemRepository
from src.repositories.tender_review_task_repository import TenderReviewTaskRepository


class TenderReviewTaskService:
    def __init__(
        self,
        task_repository: TenderReviewTaskRepository,
        item_repository: TenderReviewItemRepository,
    ) -> None:
        self.task_repository = task_repository
        self.item_repository = item_repository

    def create_task(
        self,
        *,
        project_name: str,
        review_type: str,
        document_id: str | None = None,
        document_name: str | None = None,
        document_version: str | None = None,
        created_by: str | None = None,
        status: str = "init",
        catalog_count: int = 0,
        completed_count: int = 0,
        task_no: str | None = None,
    ) -> TenderReviewTask:
        entity = TenderReviewTask(
            task_no=task_no or uuid4().hex,
            project_name=project_name,
            document_id=document_id,
            document_name=document_name,
            document_version=document_version,
            review_type=review_type,
            status=status,
            catalog_count=catalog_count,
            completed_count=completed_count,
            created_by=created_by,
        )
        return self.task_repository.create(entity)

    def get_task_by_id(self, task_id: int) -> TenderReviewTask:
        entity = self.task_repository.get_by_id(task_id)
        if entity is None:
            raise ValueError("Tender review task not found")
        return entity

    def get_task_by_task_no(self, task_no: str) -> TenderReviewTask:
        entity = self.task_repository.get_by_task_no(task_no)
        if entity is None:
            raise ValueError("Tender review task not found")
        return entity

    def list_tasks(
        self,
        *,
        status: str | None = None,
        review_type: str | None = None,
        created_by: str | None = None,
        limit: int = 100,
    ) -> list[TenderReviewTask]:
        return self.task_repository.list(
            status=status,
            review_type=review_type,
            created_by=created_by,
            limit=limit,
        )

    def update_task(
        self,
        task_id: int,
        **updates,
    ) -> TenderReviewTask:
        entity = self.get_task_by_id(task_id)
        for field in [
            "project_name",
            "document_id",
            "document_name",
            "document_version",
            "review_type",
            "status",
            "catalog_count",
            "completed_count",
            "created_by",
        ]:
            if field in updates and updates[field] is not None:
                setattr(entity, field, updates[field])
        return self.task_repository.update(entity)

    def delete_task(self, task_id: int) -> None:
        entity = self.get_task_by_id(task_id)
        self.task_repository.delete(entity)

    def create_item(
        self,
        *,
        task_id: int,
        catalog_name: str,
        parent_id: int | None = None,
        seq_no: int = 0,
        catalog_code: str | None = None,
        full_catalog_title: str | None = None,
        level: int = 1,
        source_chapter: str | None = None,
        source_pages: str | None = None,
        attached_materials: str | None = None,
        review_notes: str | None = None,
        basis_text: str | None = None,
        basis_refs_json: str | None = None,
        is_required: int = 1,
        is_scoring_related: int = 0,
        is_common_rule: int = 0,
        confidence: float | None = None,
        generation_status: str = "pending",
        manual_status: str = "unreviewed",
        manual_comment: str | None = None,
    ) -> TenderReviewItem:
        self.get_task_by_id(task_id)
        if parent_id is not None:
            self.get_item_by_id(parent_id)

        entity = TenderReviewItem(
            task_id=task_id,
            parent_id=parent_id,
            seq_no=seq_no,
            catalog_code=catalog_code,
            catalog_name=catalog_name,
            full_catalog_title=full_catalog_title,
            level=level,
            source_chapter=source_chapter,
            source_pages=source_pages,
            attached_materials=attached_materials,
            review_notes=review_notes,
            basis_text=basis_text,
            basis_refs_json=basis_refs_json,
            is_required=is_required,
            is_scoring_related=is_scoring_related,
            is_common_rule=is_common_rule,
            confidence=confidence,
            generation_status=generation_status,
            manual_status=manual_status,
            manual_comment=manual_comment,
        )
        return self.item_repository.create(entity)

    def create_items(self, items: list[dict]) -> list[TenderReviewItem]:
        entities: list[TenderReviewItem] = []
        for item in items:
            task_id = item["task_id"]
            self.get_task_by_id(task_id)
            parent_id = item.get("parent_id")
            if parent_id is not None:
                self.get_item_by_id(parent_id)
            entities.append(
                TenderReviewItem(
                    task_id=task_id,
                    parent_id=parent_id,
                    seq_no=item.get("seq_no", 0),
                    catalog_code=item.get("catalog_code"),
                    catalog_name=item["catalog_name"],
                    full_catalog_title=item.get("full_catalog_title"),
                    level=item.get("level", 1),
                    source_chapter=item.get("source_chapter"),
                    source_pages=item.get("source_pages"),
                    attached_materials=item.get("attached_materials"),
                    review_notes=item.get("review_notes"),
                    basis_text=item.get("basis_text"),
                    basis_refs_json=item.get("basis_refs_json"),
                    is_required=item.get("is_required", 1),
                    is_scoring_related=item.get("is_scoring_related", 0),
                    is_common_rule=item.get("is_common_rule", 0),
                    confidence=item.get("confidence"),
                    generation_status=item.get("generation_status", "pending"),
                    manual_status=item.get("manual_status", "unreviewed"),
                    manual_comment=item.get("manual_comment"),
                )
            )
        return self.item_repository.create_many(entities)

    def get_item_by_id(self, item_id: int) -> TenderReviewItem:
        entity = self.item_repository.get_by_id(item_id)
        if entity is None:
            raise ValueError("Tender review item not found")
        return entity

    def list_items(
        self,
        task_id: int,
        *,
        parent_id: int | None = None,
        generation_status: str | None = None,
        manual_status: str | None = None,
    ) -> list[TenderReviewItem]:
        self.get_task_by_id(task_id)
        return self.item_repository.list_by_task_id(
            task_id,
            parent_id=parent_id,
            generation_status=generation_status,
            manual_status=manual_status,
        )

    def list_all_items(self, task_id: int) -> list[TenderReviewItem]:
        self.get_task_by_id(task_id)
        return self.item_repository.list_all_by_task_id(task_id)

    def list_item_tree(self, task_id: int) -> list[dict]:
        items = self.list_all_items(task_id)
        node_map: dict[int, dict] = {}
        roots: list[dict] = []

        for item in items:
            node_map[item.id] = {"item": item, "children": []}

        for item in items:
            node = node_map[item.id]
            if item.parent_id is not None and item.parent_id in node_map:
                node_map[item.parent_id]["children"].append(node)
            else:
                roots.append(node)

        return roots

    def update_item(self, item_id: int, **updates) -> TenderReviewItem:
        entity = self.get_item_by_id(item_id)
        for field in [
            "task_id",
            "parent_id",
            "seq_no",
            "catalog_code",
            "catalog_name",
            "full_catalog_title",
            "level",
            "source_chapter",
            "source_pages",
            "attached_materials",
            "review_notes",
            "basis_text",
            "basis_refs_json",
            "is_required",
            "is_scoring_related",
            "is_common_rule",
            "confidence",
            "generation_status",
            "manual_status",
            "manual_comment",
        ]:
            if field in updates and updates[field] is not None:
                setattr(entity, field, updates[field])

        if "task_id" in updates and updates["task_id"] is not None:
            self.get_task_by_id(updates["task_id"])
        if "parent_id" in updates and updates["parent_id"] is not None:
            self.get_item_by_id(updates["parent_id"])

        return self.item_repository.update(entity)

    def delete_item(self, item_id: int) -> None:
        entity = self.get_item_by_id(item_id)
        self.item_repository.delete(entity)

    def delete_items_by_task_id(self, task_id: int) -> None:
        self.get_task_by_id(task_id)
        self.item_repository.delete_by_task_id(task_id)
