# 프로 기보에 RO(결승 제N국 등) 원문을 담는 round 컬럼을 추가하는 마이그레이션
"""Add round column to pro_games for SGF RO (game-in-series) labels.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-06

Nullable free-text column holding the raw SGF ``RO`` value (e.g. "3",
"Final 2"). Display formatting/localization happens in the web layer.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pro_games",
        sa.Column("round", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pro_games", "round")
