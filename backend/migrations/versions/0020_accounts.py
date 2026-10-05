# accounts 테이블 + sessions/games.account_id — 구글 계정 옵트인 연동.
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("provider_sub", sa.String(128), nullable=False),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("display_name", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_login_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "provider_sub", name="uq_account_provider_sub"),
    )
    # SQLite는 FK 추가를 제자리에서 못 하므로 batch 모드로 테이블을 재생성한다.
    for table in ("sessions", "games"):
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_account_id_accounts",
                "accounts",
                ["account_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index(f"ix_{table}_account_id", ["account_id"])


def downgrade() -> None:
    for table in ("games", "sessions"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_account_id")
            batch.drop_constraint(f"fk_{table}_account_id_accounts", type_="foreignkey")
            batch.drop_column("account_id")
    op.drop_table("accounts")
