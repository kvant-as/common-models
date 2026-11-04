"""plan approval path internal steps (is_internal, forwarded_to_user_id)

Revision ID: d4e5f6a7b8c0
Revises: a1b2c3d4e5f7
Create Date: 2026-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c0'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('is_internal', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('plan_approval_paths', sa.Column('forwarded_to_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_plan_approval_paths_forwarded_to_user_id',
        'plan_approval_paths', 'user',
        ['forwarded_to_user_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_plan_approval_paths_forwarded_to_user_id', 'plan_approval_paths', type_='foreignkey')
    op.drop_column('plan_approval_paths', 'forwarded_to_user_id')
    op.drop_column('plan_approval_paths', 'is_internal')
