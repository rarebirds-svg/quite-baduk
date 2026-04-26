"""Add nickname snapshot, user rank, and hint counter to games.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("games") as batch:
        # Snapshot of the session's nickname at the moment of creation. We
        # snapshot rather than joining sessions at read time because
        # ephemeral sessions may be purged before the player wants to view
        # their own history, and session_id could get reused.
        batch.add_column(sa.Column("user_nickname", sa.String(32), nullable=True))
        # The user's self-declared rank at game start — matches the same
        # allow-list the AI rank picker uses ("18k"..."7d"). Optional.
        batch.add_column(sa.Column("user_rank", sa.String(8), nullable=True))
        batch.add_column(
            sa.Column(
                "hint_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )

    # Backfill nicknames for existing games from the sessions table so
    # history views render something sensible even for older records.
    op.execute(
        """
        UPDATE games
           SET user_nickname = (
               SELECT nickname FROM sessions WHERE sessions.id = games.session_id
           )
         WHERE user_nickname IS NULL
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.drop_column("hint_count")
        batch.drop_column("user_rank")
        batch.drop_column("user_nickname")
