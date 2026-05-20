# 세션·게임에 접속 국가(CF-IPCountry 기반 2자리 코드) 컬럼을 추가하는 마이그레이션
"""Store the client's country (from Cloudflare CF-IPCountry) per session.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-21

Adds ``sessions.country`` — a 2-letter ISO 3166-1 code captured at session
creation from the ``CF-IPCountry`` header. ``games.user_country`` mirrors it
as a snapshot so the country survives session deletion (same rationale as
the ``user_nickname`` snapshot in migration 0008). Both nullable — dev /
non-Cloudflare requests have no country.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("sessions") as batch:
        batch.add_column(sa.Column("country", sa.String(length=2), nullable=True))
    with op.batch_alter_table("games") as batch:
        batch.add_column(
            sa.Column("user_country", sa.String(length=2), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("games") as batch:
        batch.drop_column("user_country")
    with op.batch_alter_table("sessions") as batch:
        batch.drop_column("country")
