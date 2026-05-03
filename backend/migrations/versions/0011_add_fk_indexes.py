"""Add foreign-key indexes on moves.game_id and analyses.game_id.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-03

Without these, the foreign-key columns we filter most often
(``moves.game_id``, ``analyses.game_id``) trigger full-table scans on
SELECTs and on cascade DELETEs. This is fine at 100 games but degrades
linearly. The fix is one migration.

Note: ``session_history.session_id`` already has ``ix_session_history_session_id``
from migration 0009 (inline ``index=True`` on the column). The composite
indexes ``ix_moves_game`` and ``ix_analyses_game_move`` from migration
0001 also cover ``game_id`` lookups via the leading column, but they are
not declared on the ORM models, so ``Base.metadata.create_all`` (used by
tests) produces a schema that drifts from production. Adding the
single-column indexes here makes the ORM truth and migration truth
match.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_moves_game_id", "moves", ["game_id"], unique=False)
    op.create_index("ix_analyses_game_id", "analyses", ["game_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_analyses_game_id", table_name="analyses")
    op.drop_index("ix_moves_game_id", table_name="moves")
