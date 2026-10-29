"""plan approval path sender snapshot (разработчик плана на момент отправки)

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8b9c0d1e2f3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('sender_post', sa.String(length=255), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('sender_name', sa.String(length=255), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('sender_phone', sa.String(length=255), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('sender_email', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('plan_approval_paths', 'sender_email')
    op.drop_column('plan_approval_paths', 'sender_phone')
    op.drop_column('plan_approval_paths', 'sender_name')
    op.drop_column('plan_approval_paths', 'sender_post')
