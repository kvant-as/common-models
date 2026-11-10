"""plan versioning (snapshot on rejection)

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b6c7d8e9f0a1'
down_revision = 'a5b6c7d8e9f0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plans', sa.Column('snapshot_of_plan_id', sa.Integer(), sa.ForeignKey('plans.id'), nullable=True))
    op.add_column('plans', sa.Column('snapshot_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('plans', 'snapshot_at')
    op.drop_column('plans', 'snapshot_of_plan_id')
