"""Add JSONB indexes

Revision ID: 0179ba46181b
Revises: 31e489628e16
Create Date: 2025-10-11 19:34:16.359206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0179ba46181b'
down_revision: Union[str, None] = '31e489628e16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create JSONB indexes for flexible queries
    op.create_index('idx_sessions_overall_score', 'interview_sessions', ['overall_score'], postgresql_using='gin')
    op.create_index('idx_answers_analysis_result', 'answers', ['analysis_result'], postgresql_using='gin')
    op.create_index('idx_answers_multi_agent_scores', 'answers', ['multi_agent_scores'], postgresql_using='gin')
    op.create_index('idx_analytics_event_data', 'analytics_events', ['event_data'], postgresql_using='gin')
    op.create_index('idx_agent_configuration', 'agent_configurations', ['configuration'], postgresql_using='gin')


def downgrade() -> None:
    # Drop JSONB indexes
    op.drop_index('idx_agent_configuration', table_name='agent_configurations')
    op.drop_index('idx_analytics_event_data', table_name='analytics_events')
    op.drop_index('idx_answers_multi_agent_scores', table_name='answers')
    op.drop_index('idx_answers_analysis_result', table_name='answers')
    op.drop_index('idx_sessions_overall_score', table_name='interview_sessions')
