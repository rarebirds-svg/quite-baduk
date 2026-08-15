# analytics_salts 테이블 생성 — 방문자 해시용 일별 솔트를 영속화한다.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_salts",
        sa.Column("day", sa.String(10), primary_key=True),
        sa.Column("salt", sa.String(64), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_salts")
