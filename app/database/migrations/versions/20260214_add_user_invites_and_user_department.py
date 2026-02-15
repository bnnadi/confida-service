"""add User.department_id and user_invites table (INT-38)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-14 10:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    users_columns = [c["name"] for c in inspector.get_columns("users")]
    if "department_id" not in users_columns:
        op.add_column("users", sa.Column("department_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_users_department_id",
            "users",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("idx_users_department_id", "users", ["department_id"])

    if "user_invites" not in tables:
        op.create_table(
            "user_invites",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=False),
            sa.Column("department_id", sa.UUID(), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
            sa.Column("invite_token", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by", sa.UUID(), nullable=False),
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
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("invite_token", name="uq_user_invites_invite_token"),
        )
        op.create_index("idx_user_invites_token", "user_invites", ["invite_token"], unique=True)
        op.create_index("idx_user_invites_organization_id", "user_invites", ["organization_id"])
        op.create_index("idx_user_invites_email", "user_invites", ["email"])
        op.create_index("idx_user_invites_status", "user_invites", ["status"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "user_invites" in tables:
        op.drop_index("idx_user_invites_status", table_name="user_invites")
        op.drop_index("idx_user_invites_email", table_name="user_invites")
        op.drop_index("idx_user_invites_organization_id", table_name="user_invites")
        op.drop_index("idx_user_invites_token", table_name="user_invites")
        op.drop_table("user_invites")

    users_columns = [c["name"] for c in inspector.get_columns("users")]
    if "department_id" in users_columns:
        op.drop_index("idx_users_department_id", table_name="users")
        op.drop_constraint("fk_users_department_id", "users", type_="foreignkey")
        op.drop_column("users", "department_id")
