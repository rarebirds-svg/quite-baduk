# sessions.nickname_key의 UNIQUE 제약을 걷어내고 일반 인덱스로 대체하는 마이그레이션
"""Drop the uniqueness of ``sessions.nickname_key``.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-16

Sessions became long-lived (90-day sliding expiry), so a unique nickname
would let one visitor lock a common name out of the service for months.
Nicknames are now free to repeat; the reserved admin keys are gated in
the session API instead. The column keeps a plain index because the
admin gate and the admin console still look sessions up by key.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # SQLite cannot drop a constraint in place — batch mode recreates the
    # table from the reflected definition minus the named constraint.
    with op.batch_alter_table("sessions") as batch:
        batch.drop_constraint("uq_sessions_nickname_key", type_="unique")
    op.create_index("ix_sessions_nickname_key", "sessions", ["nickname_key"])


def downgrade() -> None:
    op.drop_index("ix_sessions_nickname_key", table_name="sessions")
    with op.batch_alter_table("sessions") as batch:
        batch.create_unique_constraint("uq_sessions_nickname_key", ["nickname_key"])
