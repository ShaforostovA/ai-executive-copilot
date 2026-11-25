"""AI usage budgets and encrypted integration credentials."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261126_0002"
down_revision: str | None = "20261125_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("connections", sa.Column("provider_account_id", sa.String(320), nullable=True))
    op.add_column("connections", sa.Column("folder", sa.String(255), nullable=True))
    op.add_column("connections", sa.Column("sync_cursor", sa.String(128), nullable=True))

    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_ai_requests_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_ai_requests_owner_id_users",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_ai_requests_owner_created",
        "ai_requests",
        ["organization_id", "owner_id", "created_at"],
    )

    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("ciphertext", sa.String(4096), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["connection_id"],
            ["connections.id"],
            name="fk_integration_credentials_connection_id_connections",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "connection_id",
            name="uq_integration_credentials_connection_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("integration_credentials")
    op.drop_table("ai_requests")
    op.drop_column("connections", "sync_cursor")
    op.drop_column("connections", "folder")
    op.drop_column("connections", "provider_account_id")
