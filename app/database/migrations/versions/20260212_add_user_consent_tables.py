"""add user_consents and consent_history tables

Revision ID: a1b2c3d4e5f6
Revises: 75ae3d7a4ef6
Create Date: 2026-02-12 12:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "75ae3d7a4ef6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "consent_type", name="uq_user_consent_type"),
    )
    op.create_index("idx_user_consents_user_id", "user_consents", ["user_id"], unique=False)
    op.create_index("idx_user_consents_consent_type", "user_consents", ["consent_type"], unique=False)

    op.create_table(
        "consent_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_consent_history_user_id", "consent_history", ["user_id"], unique=False)
    op.create_index("idx_consent_history_consent_type", "consent_history", ["consent_type"], unique=False)
    op.create_index("idx_consent_history_created_at", "consent_history", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_consent_history_created_at", table_name="consent_history")
    op.drop_index("idx_consent_history_consent_type", table_name="consent_history")
    op.drop_index("idx_consent_history_user_id", table_name="consent_history")
    op.drop_table("consent_history")

    op.drop_index("idx_user_consents_consent_type", table_name="user_consents")
    op.drop_index("idx_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")
