"""add enterprise tables: organizations, organization_settings, departments; extend users, interview_sessions (INT-49)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-12 16:00:00.000000+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()

    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("domain", sa.String(length=255), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
        )

    if "organization_settings" not in tables:
        op.create_table(
            "organization_settings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=False),
            sa.Column("timezone", sa.String(length=50), nullable=False, server_default="UTC"),
            sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
            sa.Column(
                "features",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column(
                "notifications",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column(
                "security",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
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
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", name="uq_organization_settings_organization_id"),
        )
        op.create_index(
            "idx_organization_settings_organization_id",
            "organization_settings",
            ["organization_id"],
            unique=True,
        )

    if "departments" not in tables:
        op.create_table(
            "departments",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("organization_id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("company_id", sa.UUID(), nullable=True),
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
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_departments_organization_id", "departments", ["organization_id"])

    users_columns = [c["name"] for c in inspector.get_columns("users")]
    if "organization_id" not in users_columns:
        op.add_column("users", sa.Column("organization_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_users_organization_id",
            "users",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("idx_users_organization_id", "users", ["organization_id"])

    sessions_columns = [c["name"] for c in inspector.get_columns("interview_sessions")]
    if "organization_id" not in sessions_columns:
        op.add_column("interview_sessions", sa.Column("organization_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_sessions_organization_id",
            "interview_sessions",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("idx_sessions_organization_id", "interview_sessions", ["organization_id"])

    if "department_id" not in sessions_columns:
        op.add_column("interview_sessions", sa.Column("department_id", sa.UUID(), nullable=True))
        op.create_foreign_key(
            "fk_sessions_department_id",
            "interview_sessions",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )
        op.create_index("idx_sessions_department_id", "interview_sessions", ["department_id"])

    if "feedback" not in sessions_columns:
        op.add_column("interview_sessions", sa.Column("feedback", sa.Text(), nullable=True))

    if "duration_minutes" not in sessions_columns:
        op.add_column("interview_sessions", sa.Column("duration_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    sessions_columns = [c["name"] for c in inspector.get_columns("interview_sessions")]

    if "duration_minutes" in sessions_columns:
        op.drop_column("interview_sessions", "duration_minutes")
    if "feedback" in sessions_columns:
        op.drop_column("interview_sessions", "feedback")
    if "department_id" in sessions_columns:
        op.drop_index("idx_sessions_department_id", table_name="interview_sessions")
        op.drop_constraint("fk_sessions_department_id", "interview_sessions", type_="foreignkey")
        op.drop_column("interview_sessions", "department_id")
    if "organization_id" in sessions_columns:
        op.drop_index("idx_sessions_organization_id", table_name="interview_sessions")
        op.drop_constraint("fk_sessions_organization_id", "interview_sessions", type_="foreignkey")
        op.drop_column("interview_sessions", "organization_id")

    users_columns = [c["name"] for c in inspector.get_columns("users")]
    if "organization_id" in users_columns:
        op.drop_index("idx_users_organization_id", table_name="users")
        op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
        op.drop_column("users", "organization_id")

    op.drop_index("idx_departments_organization_id", table_name="departments")
    op.drop_table("departments")

    op.drop_index("idx_organization_settings_organization_id", table_name="organization_settings")
    op.drop_table("organization_settings")

    op.drop_table("organizations")
