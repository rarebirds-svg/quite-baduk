"""Track consecutive losing-evaluation plies for AI auto-resign guard.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-23

Adds ``games.loss_streak`` — incremented when the post-AI deep analysis
(200 visits) shows AI winrate < 1%, reset otherwise. The auto-resign
finalizer requires the streak to reach 3 so we don't resign on a single
noisy read.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.add_column(
            sa.Column(
                "loss_streak",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.drop_column("loss_streak")
