"""crawl and place enhancements

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-12
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── places: description, qdrant_id 추가 ─────────────────────────────────
    op.add_column("places", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "places",
        sa.Column(
            "qdrant_id",
            sa.UUID(as_uuid=True),
            nullable=True,
            comment="Qdrant 벡터 포인트 ID",
        ),
    )

    # ── crawl_targets: next_crawl_at, fail_count, etag, last_modified 추가 ──
    op.add_column(
        "crawl_targets",
        sa.Column("next_crawl_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crawl_targets",
        sa.Column(
            "fail_count",
            sa.SmallInteger(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "crawl_targets",
        sa.Column("etag", sa.String(128), nullable=True),
    )
    op.add_column(
        "crawl_targets",
        sa.Column(
            "last_modified",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="HTTP Last-Modified 헤더 — If-Modified-Since 조건부 요청용",
        ),
    )

    # ── crawl_logs: http_status_code, duration_ms, retry_of 추가 ────────────
    op.add_column(
        "crawl_logs",
        sa.Column("http_status_code", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "crawl_logs",
        sa.Column("duration_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "crawl_logs",
        sa.Column(
            "retry_of",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("crawl_logs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── 인덱스 추가 ──────────────────────────────────────────────────────────
    op.create_index(
        "ix_places_qdrant_id",
        "places",
        ["qdrant_id"],
        unique=True,
        postgresql_where=sa.text("qdrant_id IS NOT NULL"),
    )
    op.create_index(
        "ix_crawl_targets_next_crawl_at",
        "crawl_targets",
        ["next_crawl_at"],
        postgresql_where=sa.text("is_active = true AND next_crawl_at IS NOT NULL"),
    )
    op.create_index(
        "ix_crawl_logs_retry_of",
        "crawl_logs",
        ["retry_of"],
        postgresql_where=sa.text("retry_of IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_logs_retry_of", table_name="crawl_logs")
    op.drop_index("ix_crawl_targets_next_crawl_at", table_name="crawl_targets")
    op.drop_index("ix_places_qdrant_id", table_name="places")

    op.drop_column("crawl_logs", "retry_of")
    op.drop_column("crawl_logs", "duration_ms")
    op.drop_column("crawl_logs", "http_status_code")

    op.drop_column("crawl_targets", "last_modified")
    op.drop_column("crawl_targets", "etag")
    op.drop_column("crawl_targets", "fail_count")
    op.drop_column("crawl_targets", "next_crawl_at")

    op.drop_column("places", "qdrant_id")
    op.drop_column("places", "description")
