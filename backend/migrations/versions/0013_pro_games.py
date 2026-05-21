# 프로 기보(pro_games) 테이블을 생성하는 마이그레이션
"""Create the pro_games table for spectatable professional game records.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-21

Stores public-domain professional game records (move sequences only, no
commentary) for the spectate area. ``content_hash`` is UNIQUE so the seed
script and admin upload can dedup. No moves table — moves are parsed from
``sgf`` on read.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pro_games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection", sa.String(length=16), nullable=False),
        sa.Column("black_player", sa.String(length=64), nullable=False),
        sa.Column("white_player", sa.String(length=64), nullable=False),
        sa.Column("black_rank", sa.String(length=16), nullable=True),
        sa.Column("white_rank", sa.String(length=16), nullable=True),
        sa.Column("event", sa.String(length=128), nullable=True),
        sa.Column("game_date", sa.Date(), nullable=True),
        sa.Column("result", sa.String(length=16), nullable=True),
        sa.Column("board_size", sa.Integer(), nullable=False),
        sa.Column("handicap", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("komi", sa.Float(), nullable=False, server_default="6.5"),
        sa.Column("move_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sgf", sa.Text(), nullable=False),
        sa.Column("source_note", sa.String(length=256), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("content_hash", name="uq_pro_games_content_hash"),
    )
    op.create_index("ix_pro_games_collection", "pro_games", ["collection"])


def downgrade() -> None:
    op.drop_table("pro_games")
