"""add user_goals table

Revision ID: 75ae3d7a4ef6
Revises: 20250116_add_role
Create Date: 2026-02-12 04:12:23.462781+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "75ae3d7a4ef6"
down_revision: Union[str, None] = "20250116_add_role"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_goals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goal_type", sa.String(length=50), nullable=False),
        sa.Column("target_value", sa.Float(), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dimension", sa.String(length=100), nullable=True),
        sa.Column("target_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
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
    )
    op.create_index("idx_user_goals_user_id", "user_goals", ["user_id"], unique=False)
    op.create_index("idx_user_goals_status", "user_goals", ["status"], unique=False)
    op.create_index("idx_user_goals_goal_type", "user_goals", ["goal_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_user_goals_goal_type", table_name="user_goals")
    op.drop_index("idx_user_goals_status", table_name="user_goals")
    op.drop_index("idx_user_goals_user_id", table_name="user_goals")
    op.drop_table("user_goals")
