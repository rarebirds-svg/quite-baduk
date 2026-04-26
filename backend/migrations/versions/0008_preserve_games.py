"""Preserve games history across session deletion.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-23

Rationale
---------
Sessions are ephemeral (users log in by nickname, rows get purged on logout
or idle TTL). Originally the ``games.session_id`` FK was ``ON DELETE CASCADE``
so ending a session wiped the user's entire game history — which also
destroyed the admin console's audit trail.

We want games (and their moves) to live beyond their originating session:

* Make ``games.session_id`` nullable.
* Change the FK to ``ON DELETE SET NULL`` so deleting a session just detaches
  its games rather than removing them.
* ``games.user_nickname`` was already snapshotted in migration 0007, so the
  admin view has a name to display even after the session is gone.

SQLite cannot alter a FK in place, so we force Alembic's batch mode to
recreate the table from the ORM's declared schema via ``recreate="always"``.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table(
        "games",
        recreate="always",
        table_args=(
            sa.ForeignKeyConstraint(
                ["session_id"], ["sessions.id"], ondelete="SET NULL"
            ),
        ),
    ) as batch:
        batch.alter_column(
            "session_id",
            existing_type=sa.Integer(),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table(
        "games",
        recreate="always",
        table_args=(
            sa.ForeignKeyConstraint(
                ["session_id"], ["sessions.id"], ondelete="CASCADE"
            ),
        ),
    ) as batch:
        batch.alter_column(
            "session_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
