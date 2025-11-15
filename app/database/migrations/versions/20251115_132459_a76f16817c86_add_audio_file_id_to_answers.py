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
    # Add audio_file_id column to answers table
    op.add_column("answers", sa.Column("audio_file_id", sa.String(255), nullable=True))
    # Create index on audio_file_id for faster lookups
    op.create_index("ix_answers_audio_file_id", "answers", ["audio_file_id"])


def downgrade() -> None:
    # Drop index and column
    op.drop_index("ix_answers_audio_file_id", table_name="answers")
    op.drop_column("answers", "audio_file_id")
