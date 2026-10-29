"""plan approval path cycle (история циклов отправки плана)

Revision ID: d5e6f7a8b9c0
Revises: b2c3d4e5f6a7
Create Date: 2026-10-26
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'plan_approval_paths',
        sa.Column('cycle', sa.Integer(), nullable=False, server_default='1'),
    )


def downgrade():
    op.drop_column('plan_approval_paths', 'cycle')
