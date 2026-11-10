"""plan approval path log_action (Шаг 2 history inside external orgs)

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c0
Create Date: 2026-11-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1f2a3b4c5d6'
down_revision = 'd4e5f6a7b8c0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('log_action', sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column('plan_approval_paths', 'log_action')
