"""Ephemeral nickname sessions — drop users, add sessions, rename games FK

Pre-launch: wipes all user-owned rows. Replaces the persistent users
table with an ephemeral sessions table scoped to a single browser
session. Games now FK to sessions(id) with ON DELETE CASCADE so a
session end wipes all owned games/moves/analyses.

Revision ID: 0005
Revises: 0004
Create Date: 2026-04-22
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop everything user-scoped. Pre-launch: data loss accepted.
    op.drop_index("ix_analyses_game_move", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_moves_game", table_name="moves")
    op.drop_table("moves")
    op.drop_index("ix_games_user_status", table_name="games")
    op.drop_table("games")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("nickname", sa.String(32), nullable=False),
        sa.Column("nickname_key", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("token", name="uq_sessions_token"),
        sa.UniqueConstraint("nickname_key", name="uq_sessions_nickname_key"),
    )
    op.create_index("ix_sessions_token", "sessions", ["token"])

    op.create_table(
        "games",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_id", sa.Integer, nullable=False),
        sa.Column("ai_rank", sa.String(8), nullable=False),
        sa.Column("ai_style", sa.String(16), nullable=False, server_default="balanced"),
        sa.Column("ai_player", sa.String(32), nullable=True),
        sa.Column("handicap", sa.Integer, nullable=False, server_default="0"),
        sa.Column("board_size", sa.Integer, nullable=False, server_default="19"),
        sa.Column("komi", sa.Float, nullable=False, server_default="6.5"),
        sa.Column("user_color", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("result", sa.String(16), nullable=True),
        sa.Column("winner", sa.String(8), nullable=True),
        sa.Column("move_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("sgf_cache", sa.Text, nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_games_session_status", "games", ["session_id", "status"])

    op.create_table(
        "moves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("color", sa.String(2), nullable=False),
        sa.Column("coord", sa.String(4), nullable=True),
        sa.Column("captures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_undone", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("played_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_game_move"),
    )
    op.create_index("ix_moves_game", "moves", ["game_id", "move_number"])

    op.create_table(
        "analyses",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("game_id", sa.Integer, nullable=False),
        sa.Column("move_number", sa.Integer, nullable=False),
        sa.Column("payload", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id", "move_number", name="uq_analysis_game_move"),
    )
    op.create_index("ix_analyses_game_move", "analyses", ["game_id", "move_number"])


def downgrade() -> None:
    op.drop_index("ix_analyses_game_move", table_name="analyses")
    op.drop_table("analyses")
    op.drop_index("ix_moves_game", table_name="moves")
    op.drop_table("moves")
    op.drop_index("ix_games_session_status", table_name="games")
    op.drop_table("games")
    op.drop_index("ix_sessions_token", table_name="sessions")
    op.drop_table("sessions")
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("preferred_rank", sa.String(8), nullable=True),
        sa.Column("locale", sa.String(4), nullable=False, server_default="ko"),
        sa.Column("theme", sa.String(8), nullable=False, server_default="light"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
