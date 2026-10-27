"""plan approval path viewed_by (кто поставил подпись)

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-10-27
"""
from alembic import op
import sqlalchemy as sa

revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'plan_approval_paths',
        sa.Column('viewed_by_user_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_plan_approval_paths_viewed_by_user_id',
        'plan_approval_paths', 'user',
        ['viewed_by_user_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_plan_approval_paths_viewed_by_user_id', 'plan_approval_paths', type_='foreignkey')
    op.drop_column('plan_approval_paths', 'viewed_by_user_id')
