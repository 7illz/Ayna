"""add review audit trail

Revision ID: 8a9c2d41f603
Revises: 3557181ba1d8
"""

import sqlalchemy as sa
from alembic import op

revision = "8a9c2d41f603"
down_revision = "3557181ba1d8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("seller_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("notes", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('approve','reject')", name="review_audit_decision"),
        sa.ForeignKeyConstraint(["job_id"], ["generation_jobs.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_audits_job_id"), "review_audits", ["job_id"])
    op.create_index(op.f("ix_review_audits_product_id"), "review_audits", ["product_id"])
    op.create_index(op.f("ix_review_audits_seller_id"), "review_audits", ["seller_id"])


def downgrade():
    op.drop_index(op.f("ix_review_audits_seller_id"), table_name="review_audits")
    op.drop_index(op.f("ix_review_audits_product_id"), table_name="review_audits")
    op.drop_index(op.f("ix_review_audits_job_id"), table_name="review_audits")
    op.drop_table("review_audits")
