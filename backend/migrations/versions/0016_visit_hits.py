# visit_hits 테이블 생성 — 방문 통계 원장.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "visit_hits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("referrer_host", sa.String(255), nullable=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("visitor_hash", sa.String(64), nullable=False),
        sa.Column("device", sa.String(16), nullable=True),
    )
    op.create_index("ix_visit_hits_created_at", "visit_hits", ["created_at"])
    op.create_index("ix_visit_hits_path", "visit_hits", ["path"])
    op.create_index("ix_visit_hits_source", "visit_hits", ["source"])
    op.create_index("ix_visit_hits_country", "visit_hits", ["country"])


def downgrade() -> None:
    op.drop_table("visit_hits")
