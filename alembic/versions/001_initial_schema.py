"""Initial database schema for call analytics

Revision ID: 001
Revises: 
Create Date: 2024-01-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create calls table
    op.create_table('calls',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('dispatch_id', sa.String(length=255), nullable=False),
        sa.Column('room_name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('transfer_to_number', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('end_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispatch_id')
    )
    op.create_index('idx_calls_dispatch_id', 'calls', ['dispatch_id'])
    op.create_index('idx_calls_phone_number', 'calls', ['phone_number'])
    op.create_index('idx_calls_status', 'calls', ['status'])

    # Create call_connection_metrics table
    op.create_table('call_connection_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dispatch_created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dispatch_accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('room_connection_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('room_connection_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('room_connection_duration_ms', sa.Integer(), nullable=True),
        sa.Column('agent_init_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_init_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agent_init_duration_ms', sa.Integer(), nullable=True),
        sa.Column('session_creation_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_creation_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('session_creation_duration_ms', sa.Integer(), nullable=True),
        sa.Column('sip_dial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sip_dial_completed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sip_dial_duration_ms', sa.Integer(), nullable=True),
        sa.Column('sip_dial_status', sa.String(length=50), nullable=True),
        sa.Column('call_answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('participant_joined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_setup_time_ms', sa.Integer(), nullable=True),
        sa.Column('time_to_connect_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Create call_interaction_metrics table
    op.create_table('call_interaction_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('call_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('call_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_duration_seconds', sa.Float(), nullable=True),
        sa.Column('agent_first_speech_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_first_speech_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_to_first_agent_response_ms', sa.Integer(), nullable=True),
        sa.Column('time_to_first_user_response_ms', sa.Integer(), nullable=True),
        sa.Column('total_agent_utterances', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_user_utterances', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_interruptions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_silence_periods', sa.Integer(), server_default='0', nullable=True),
        sa.Column('total_silence_duration_ms', sa.Integer(), server_default='0', nullable=True),
        sa.Column('avg_agent_response_time_ms', sa.Float(), nullable=True),
        sa.Column('max_agent_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('min_agent_response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Create call_speech_analytics table
    op.create_table('call_speech_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('total_words_spoken_agent', sa.Integer(), nullable=True),
        sa.Column('total_words_spoken_user', sa.Integer(), nullable=True),
        sa.Column('avg_words_per_minute_agent', sa.Float(), nullable=True),
        sa.Column('avg_words_per_minute_user', sa.Float(), nullable=True),
        sa.Column('user_sentiment_score', sa.Float(), nullable=True),
        sa.Column('detected_user_emotion', sa.String(length=50), nullable=True),
        sa.Column('avg_confidence_score', sa.Float(), nullable=True),
        sa.Column('low_confidence_utterances', sa.Integer(), nullable=True),
        sa.Column('topic_changes', sa.Integer(), nullable=True),
        sa.Column('clarification_requests', sa.Integer(), nullable=True),
        sa.Column('transcript', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Create call_system_metrics table
    op.create_table('call_system_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('peak_cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('avg_cpu_usage_percent', sa.Float(), nullable=True),
        sa.Column('peak_memory_usage_mb', sa.Integer(), nullable=True),
        sa.Column('avg_memory_usage_mb', sa.Integer(), nullable=True),
        sa.Column('total_bandwidth_used_mb', sa.Float(), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('packet_loss_percent', sa.Float(), nullable=True),
        sa.Column('llm_requests_count', sa.Integer(), nullable=True),
        sa.Column('llm_total_tokens_used', sa.Integer(), nullable=True),
        sa.Column('llm_avg_response_time_ms', sa.Float(), nullable=True),
        sa.Column('stt_processing_time_ms', sa.Float(), nullable=True),
        sa.Column('tts_processing_time_ms', sa.Float(), nullable=True),
        sa.Column('error_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('warning_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id')
    )

    # Create call_events table
    op.create_table('call_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_from_call_start_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_call_events_call_id', 'call_events', ['call_id'])
    op.create_index('idx_call_events_timestamp', 'call_events', ['event_timestamp'])
    op.create_index('idx_call_events_type', 'call_events', ['event_type'])


def downgrade() -> None:
    op.drop_index('idx_call_events_type', table_name='call_events')
    op.drop_index('idx_call_events_timestamp', table_name='call_events')
    op.drop_index('idx_call_events_call_id', table_name='call_events')
    op.drop_table('call_events')
    op.drop_table('call_system_metrics')
    op.drop_table('call_speech_analytics')
    op.drop_table('call_interaction_metrics')
    op.drop_table('call_connection_metrics')
    op.drop_index('idx_calls_status', table_name='calls')
    op.drop_index('idx_calls_phone_number', table_name='calls')
    op.drop_index('idx_calls_dispatch_id', table_name='calls')
    op.drop_table('calls')