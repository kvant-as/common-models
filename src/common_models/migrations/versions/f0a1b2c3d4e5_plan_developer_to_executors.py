"""move plan developer info from plans to plan_executors

Revision ID: f0a1b2c3d4e5
Revises: e9f0a1b2c3d4
Create Date: 2026-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f0a1b2c3d4e5'
down_revision = 'e9f0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_executors', sa.Column('is_developer', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('plan_executors', sa.Column('developer_name', sa.String(length=255), nullable=True))
    op.add_column('plan_executors', sa.Column('developer_phone', sa.String(length=255), nullable=True))
    op.add_column('plan_executors', sa.Column('developer_email', sa.String(length=255), nullable=True))

    op.drop_column('plans', 'developer_name')
    op.drop_column('plans', 'developer_phone')
    op.drop_column('plans', 'developer_email')


def downgrade():
    op.add_column('plans', sa.Column('developer_email', sa.String(length=255), nullable=True))
    op.add_column('plans', sa.Column('developer_phone', sa.String(length=255), nullable=True))
    op.add_column('plans', sa.Column('developer_name', sa.String(length=255), nullable=True))

    op.drop_column('plan_executors', 'developer_email')
    op.drop_column('plan_executors', 'developer_phone')
    op.drop_column('plan_executors', 'developer_name')
    op.drop_column('plan_executors', 'is_developer')
