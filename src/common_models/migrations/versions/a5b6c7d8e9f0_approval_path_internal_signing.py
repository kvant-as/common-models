"""internal signing cycle for PlanApprovalPath (step 2)

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a5b6c7d8e9f0'
down_revision = 'f4a5b6c7d8e9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('pending_signer_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('is_signed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('plan_approval_paths', sa.Column('submitted_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('pending_decision', sa.String(length=20), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('signed_by_user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('signed_at', sa.DateTime(), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('signed_by_snapshot', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('plan_approval_paths', 'signed_by_snapshot')
    op.drop_column('plan_approval_paths', 'signed_at')
    op.drop_column('plan_approval_paths', 'signed_by_user_id')
    op.drop_column('plan_approval_paths', 'pending_decision')
    op.drop_column('plan_approval_paths', 'submitted_by_user_id')
    op.drop_column('plan_approval_paths', 'is_signed')
    op.drop_column('plan_approval_paths', 'pending_signer_user_id')
