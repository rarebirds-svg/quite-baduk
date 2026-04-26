"""Add ai_style to games.

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-21
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.add_column(
            sa.Column(
                "ai_style",
                sa.String(16),
                nullable=False,
                server_default="balanced",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.drop_column("ai_style")
