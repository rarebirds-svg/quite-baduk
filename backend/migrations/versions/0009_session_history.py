"""Append-only session login history for admin audit.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-23

Rationale
---------
Ephemeral sessions (``sessions`` table) are purged on logout or idle TTL,
which loses the record of who connected and when. This is fine for the
live view but breaks any retrospective look at traffic.

``session_history`` is a simple append-only log:

* ``created_at`` is set when a session is first registered.
* ``ended_at`` + ``end_reason`` are populated when the originating session
  leaves (via logout, idle purge, or SESSION_REPLACED WS eviction). Rows
  without an ``ended_at`` represent sessions that never cleanly ended.

No FK to ``sessions`` — the table is intentionally outlive-able.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=True, index=True),
        sa.Column("nickname", sa.String(32), nullable=False),
        sa.Column("nickname_key", sa.String(32), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("end_reason", sa.String(16), nullable=True),
    )
    op.create_index(
        "ix_session_history_created_at", "session_history", ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_session_history_created_at", table_name="session_history")
    op.drop_table("session_history")
