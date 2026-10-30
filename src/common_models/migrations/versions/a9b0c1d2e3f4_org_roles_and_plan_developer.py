"""org roles and plan developer info

Revision ID: a9b0c1d2e3f4
Revises: e7f8a9b0c1d2
Create Date: 2026-10-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a9b0c1d2e3f4'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('org_role', sa.String(length=30), nullable=True))
    op.add_column('plans', sa.Column('developer_name', sa.String(length=255), nullable=True))
    op.add_column('plans', sa.Column('developer_phone', sa.String(length=255), nullable=True))
    op.add_column('plans', sa.Column('developer_email', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('plans', 'developer_email')
    op.drop_column('plans', 'developer_phone')
    op.drop_column('plans', 'developer_name')
    op.drop_column('user', 'org_role')
