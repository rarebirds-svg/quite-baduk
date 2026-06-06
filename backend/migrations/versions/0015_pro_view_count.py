# pro_games에 view_count 추가 + 기존 cwi/recent 행을 base(world/masterpiece)로 재분류
"""Add view_count and reclassify cwi/recent rows into base collections.

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-06

view_count(인기순 정렬용)을 추가하고, ingest가 'cwi'로 적재했던 행을 event 기준
국제기전→'world', 그 외→'masterpiece'로 재분류한다. 재분류는 비가역이라 downgrade는
view_count 컬럼만 제거한다.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pro_games",
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        "UPDATE pro_games SET collection='world' "
        "WHERE collection IN ('cwi','recent') AND ("
        "lower(event) LIKE '%chunlan%' OR lower(event) LIKE '%fujitsu%' "
        "OR lower(event) LIKE '%ing cup%' OR lower(event) LIKE '%lg cup%' "
        "OR lower(event) LIKE '%samsung%' OR lower(event) LIKE '%toyota%')"
    )
    op.execute(
        "UPDATE pro_games SET collection='masterpiece' "
        "WHERE collection IN ('cwi','recent')"
    )


def downgrade() -> None:
    op.drop_column("pro_games", "view_count")
