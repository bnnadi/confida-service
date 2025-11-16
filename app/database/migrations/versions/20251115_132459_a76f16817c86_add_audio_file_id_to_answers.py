"""add_audio_file_id_to_answers

Revision ID: a76f16817c86
Revises: f73a0d61689a
Create Date: 2025-11-15 13:24:59.107186+00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a76f16817c86"
down_revision: Union[str, None] = "f73a0d61689a"
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
    
    def index_exists(table_name, index_name):
        try:
            indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
            return index_name in indexes
        except Exception:
            return False
    
    # Add audio_file_id column to answers table if it doesn't exist
    if table_exists("answers"):
        if not column_exists("answers", "audio_file_id"):
            op.add_column("answers", sa.Column("audio_file_id", sa.String(255), nullable=True))
        
        # Create index on audio_file_id for faster lookups if it doesn't exist
        if not index_exists("answers", "ix_answers_audio_file_id"):
            op.create_index("ix_answers_audio_file_id", "answers", ["audio_file_id"])


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
    if index_exists("answers", "ix_answers_audio_file_id"):
        op.drop_index("ix_answers_audio_file_id", table_name="answers")
    if column_exists("answers", "audio_file_id"):
        op.drop_column("answers", "audio_file_id")
