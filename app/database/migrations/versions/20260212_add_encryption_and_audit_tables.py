"""add encryption_keys, data_access_log, and session_id on answers (INT-31)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-12 14:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "encryption_keys" not in tables:
        op.create_table(
            "encryption_keys",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column("key_salt", sa.String(length=88), nullable=False),
            sa.Column("key_version", sa.Integer(), nullable=False, server_default="1"),
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
            sa.UniqueConstraint("user_id", name="uq_encryption_keys_user_id"),
        )
        op.create_index("idx_encryption_keys_user_id", "encryption_keys", ["user_id"], unique=True)

    if "data_access_log" not in tables:
        op.create_table(
            "data_access_log",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=True),
            sa.Column("resource_type", sa.String(length=50), nullable=False),
            sa.Column("resource_id", sa.String(length=255), nullable=True),
            sa.Column("action", sa.String(length=20), nullable=False),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_data_access_log_user_id", "data_access_log", ["user_id"], unique=False)
        op.create_index("idx_data_access_log_created_at", "data_access_log", ["created_at"], unique=False)
        op.create_index("idx_data_access_log_resource_type", "data_access_log", ["resource_type"], unique=False)

    answers_columns = [c["name"] for c in inspector.get_columns("answers")]
    if "session_id" not in answers_columns:
        op.add_column("answers", sa.Column("session_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_answers_session_id",
            "answers",
            "interview_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )
        op.create_index("idx_answers_session_id", "answers", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_answers_session_id", table_name="answers")
    op.drop_constraint("fk_answers_session_id", "answers", type_="foreignkey")
    op.drop_column("answers", "session_id")

    op.drop_index("idx_data_access_log_resource_type", table_name="data_access_log")
    op.drop_index("idx_data_access_log_created_at", table_name="data_access_log")
    op.drop_index("idx_data_access_log_user_id", table_name="data_access_log")
    op.drop_table("data_access_log")

    op.drop_index("idx_encryption_keys_user_id", table_name="encryption_keys")
    op.drop_table("encryption_keys")
