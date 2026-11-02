from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.db import Base


def new_id() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(UTC)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "publish_status IN ('draft','generating','needs_review','approved','rejected')",
            name="product_publish_status",
        ),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    seller_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(String(3000), default="")
    publish_status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    images: Mapped[list["ProductImage"]] = relationship(
        cascade="all, delete-orphan", order_by="ProductImage.sort_order", lazy="selectin"
    )


class ProductImage(Base):
    __tablename__ = "product_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    original_key: Mapped[str] = mapped_column(String(255))
    view_tag: Mapped[str] = mapped_column(String(32), default="unspecified")
    sort_order: Mapped[int]


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = (
        UniqueConstraint("product_id", "idempotency_key", name="uq_generation_request"),
        CheckConstraint(
            "status IN ('queued','processing','succeeded','failed','cancelled')", name="job_status"
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="job_progress"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    provider: Mapped[str] = mapped_column(String(32), default="mock")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    progress: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None] = mapped_column(String(64))
    model_key: Mapped[str | None] = mapped_column(String(255))
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)


class QualityReport(Base):
    __tablename__ = "quality_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','pass','needs_review','failed','not_evaluated')",
            name="quality_status",
        ),
    )
    job_id: Mapped[str] = mapped_column(ForeignKey("generation_jobs.id"), primary_key=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="not_evaluated")
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(String(3000), default="")
    uncertain_views: Mapped[list] = mapped_column(JSON, default=list)
    reviewed_by: Mapped[str | None] = mapped_column(String(36))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewAudit(Base):
    """Append-only seller decisions for publication and revocation."""

    __tablename__ = "review_audits"
    __table_args__ = (
        CheckConstraint("decision IN ('approve','reject')", name="review_audit_decision"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("generation_jobs.id"), index=True)
    seller_id: Mapped[str] = mapped_column(String(36), index=True)
    decision: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str] = mapped_column(String(2000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
