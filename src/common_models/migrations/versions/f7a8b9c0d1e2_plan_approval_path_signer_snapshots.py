"""plan approval path signer snapshots (должность/ФИО на момент подписи/отклонения)

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'plan_approval_paths',
        sa.Column('viewed_by_snapshot', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'plan_approval_paths',
        sa.Column('rejected_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'plan_approval_paths',
        sa.Column('rejected_by_snapshot', sa.String(length=255), nullable=True),
    )


def downgrade():
    op.drop_column('plan_approval_paths', 'rejected_by_snapshot')
    op.drop_column('plan_approval_paths', 'rejected_at')
    op.drop_column('plan_approval_paths', 'viewed_by_snapshot')
