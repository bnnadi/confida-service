"""add_role_column_to_users

Revision ID: 20250116_add_role
Revises: 84cb1aaf7a64
Create Date: 2025-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250116_add_role'
down_revision: Union[str, None] = 'a76f16817c86'  # Points to latest migration to merge branches
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Helper functions
    def table_exists(table_name):
        try:
            return table_name in inspector.get_table_names()
        except Exception:
            return False
    
    def column_exists(table_name, column_name):
        try:
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
        except Exception:
            return False
    
    # Add role column to users table if it doesn't exist
    if table_exists("users"):
        if not column_exists("users", "role"):
            op.add_column(
                "users",
                sa.Column(
                    "role",
                    sa.String(50),
                    nullable=False,
                    server_default="user"  # Default existing users to "user"
                )
            )
            
            # Create index on role for faster lookups
            op.create_index("ix_users_role", "users", ["role"])


def downgrade() -> None:
    from sqlalchemy import inspect
    
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Helper functions
    def index_exists(table_name, index_name):
        try:
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            return index_name in indexes
        except Exception:
            return False
    
    def column_exists(table_name, column_name):
        try:
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            return column_name in columns
        except Exception:
            return False
    
    # Drop index and column if they exist
    if index_exists("users", "ix_users_role"):
        op.drop_index("ix_users_role", table_name="users")
    if column_exists("users", "role"):
        op.drop_column("users", "role")

