# search_queries 테이블 생성 — 검색 콘솔 검색어 통계.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "search_queries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(8), nullable=False),
        sa.Column("query", sa.String(255), nullable=False),
        sa.Column("page", sa.String(512), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("impressions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ctr", sa.Float(), nullable=False, server_default="0"),
        sa.Column("position", sa.Float(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source", "query", "page", "date", name="uq_search_query"),
    )
    op.create_index("ix_search_queries_source", "search_queries", ["source"])
    op.create_index("ix_search_queries_date", "search_queries", ["date"])


def downgrade() -> None:
    op.drop_table("search_queries")
