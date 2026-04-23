from datetime import datetime

from sqlalchemy import BIGINT, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class TenderReviewItem(Base):
    __tablename__ = "tender_review_item"

    id: Mapped[int] = mapped_column(BIGINT(), primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BIGINT(),
        ForeignKey("tender_review_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BIGINT(),
        ForeignKey("tender_review_item.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    seq_no: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    catalog_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    catalog_name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_catalog_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    level: Mapped[int] = mapped_column(nullable=False, default=1, index=True)
    source_chapter: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_pages: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attached_materials: Mapped[str | None] = mapped_column(
        Text().with_variant(Text(length=4294967295), "mysql"),
        nullable=True,
    )
    review_notes: Mapped[str | None] = mapped_column(
        Text().with_variant(Text(length=4294967295), "mysql"),
        nullable=True,
    )
    basis_text: Mapped[str | None] = mapped_column(
        Text().with_variant(Text(length=4294967295), "mysql"),
        nullable=True,
    )
    basis_refs_json: Mapped[str | None] = mapped_column(
        Text().with_variant(Text(length=4294967295), "mysql"),
        nullable=True,
    )
    is_required: Mapped[int] = mapped_column(nullable=False, default=1, index=True)
    is_scoring_related: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    is_common_rule: Mapped[int] = mapped_column(nullable=False, default=0, index=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    generation_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True,
    )
    manual_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unreviewed",
        index=True,
    )
    manual_comment: Mapped[str | None] = mapped_column(
        Text().with_variant(Text(length=4294967295), "mysql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
