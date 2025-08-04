"""add call recording table

Revision ID: 002
Revises: 001
Create Date: 2025-08-04

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create call_recordings table
    op.create_table('call_recordings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('call_id', sa.String(), nullable=False),
        sa.Column('egress_id', sa.String(length=100), nullable=False),
        sa.Column('room_name', sa.String(length=100), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('format', sa.String(length=20), nullable=True, server_default='mp4'),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='recording'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['call_id'], ['calls.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('call_id'),
        sa.UniqueConstraint('egress_id')
    )


def downgrade():
    # Drop call_recordings table
    op.drop_table('call_recordings')