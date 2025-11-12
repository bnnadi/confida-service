"""Add JSONB indexes

Revision ID: 0179ba46181b
Revises: 31e489628e16
Create Date: 2025-10-11 19:34:16.359206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '0179ba46181b'
down_revision: Union[str, None] = '31e489628e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(connection, table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(connection)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    # Create JSONB indexes for flexible queries
    # Only create indexes if the tables exist
    connection = op.get_bind()
    
    if _table_exists(connection, 'interview_sessions'):
        try:
            op.create_index('idx_sessions_overall_score', 'interview_sessions', ['overall_score'], postgresql_using='gin')
        except Exception:
            # Index might already exist, skip
            pass
    
    if _table_exists(connection, 'answers'):
        try:
            op.create_index('idx_answers_analysis_result', 'answers', ['analysis_result'], postgresql_using='gin')
        except Exception:
            pass
        try:
            op.create_index('idx_answers_multi_agent_scores', 'answers', ['multi_agent_scores'], postgresql_using='gin')
        except Exception:
            pass
    
    if _table_exists(connection, 'analytics_events'):
        try:
            op.create_index('idx_analytics_event_data', 'analytics_events', ['event_data'], postgresql_using='gin')
        except Exception:
            pass
    
    if _table_exists(connection, 'agent_configurations'):
        try:
            op.create_index('idx_agent_configuration', 'agent_configurations', ['configuration'], postgresql_using='gin')
        except Exception:
            pass


def downgrade() -> None:
    # Drop JSONB indexes
    connection = op.get_bind()
    
    if _table_exists(connection, 'agent_configurations'):
        try:
            op.drop_index('idx_agent_configuration', table_name='agent_configurations')
        except Exception:
            pass
    
    if _table_exists(connection, 'analytics_events'):
        try:
            op.drop_index('idx_analytics_event_data', table_name='analytics_events')
        except Exception:
            pass
    
    if _table_exists(connection, 'answers'):
        try:
            op.drop_index('idx_answers_multi_agent_scores', table_name='answers')
        except Exception:
            pass
        try:
            op.drop_index('idx_answers_analysis_result', table_name='answers')
        except Exception:
            pass
    
    if _table_exists(connection, 'interview_sessions'):
        try:
            op.drop_index('idx_sessions_overall_score', table_name='interview_sessions')
        except Exception:
            pass
