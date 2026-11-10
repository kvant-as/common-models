"""add PlanApprovalPath.remark, add 'signer' step support, drop Plan.internal_return_reason

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('remark', sa.String(length=500), nullable=True))
    # Замечание о возврате без подписи теперь хранится на самом этапе
    # (PlanApprovalPath, step_type='signer'), а не на плане — для планов,
    # уже возвращённых на доработку до этой миграции, соответствующего
    # этапа ещё не существует, так что старый текст некуда перенести.
    op.drop_column('plans', 'internal_return_reason')


def downgrade():
    op.add_column('plans', sa.Column('internal_return_reason', sa.String(length=500), nullable=True))
    op.drop_column('plan_approval_paths', 'remark')
