"""plan internal signing cycle

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'b0c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plans', sa.Column('internal_status', sa.String(length=20), nullable=True))
    op.add_column('plans', sa.Column('pending_signer_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plans', sa.Column('submitted_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plans', sa.Column('internal_return_reason', sa.String(length=500), nullable=True))
    op.add_column('plans', sa.Column('internal_signed_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plans', sa.Column('internal_signed_at', sa.DateTime(), nullable=True))
    op.add_column('plans', sa.Column('internal_signed_by_snapshot', sa.String(length=255), nullable=True))
    op.add_column('plans', sa.Column('pending_coordinator_ids', sa.String(length=500), nullable=True))
    op.add_column('plans', sa.Column('pending_approver_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('plans', 'pending_approver_id')
    op.drop_column('plans', 'pending_coordinator_ids')
    op.drop_column('plans', 'internal_signed_by_snapshot')
    op.drop_column('plans', 'internal_signed_at')
    op.drop_column('plans', 'internal_signed_by_user_id')
    op.drop_column('plans', 'internal_return_reason')
    op.drop_column('plans', 'submitted_by_user_id')
    op.drop_column('plans', 'pending_signer_user_id')
    op.drop_column('plans', 'internal_status')
