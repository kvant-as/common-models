"""drop unused user.type and user.fio columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-23 00:00:00.000000

Neither column is written anywhere in either application — `type` (default
'Респондент') is never read either, and `fio` is only ever read as the first
link in a fallback chain (`user.fio or <computed full name> or user.email`)
that always falls through since nothing ever sets it.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column('user', 'type')
    op.drop_column('user', 'fio')


def downgrade():
    op.add_column('user', sa.Column('fio', sa.String(length=100), nullable=True))
    op.add_column('user', sa.Column('type', sa.String(length=13), nullable=True, server_default='Респондент'))
