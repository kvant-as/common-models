"""user is_verified flag

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-11-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e9f0a1b2c3d4'
down_revision = 'd8e9f0a1b2c3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'user',
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=True),
    )


def downgrade():
    op.drop_column('user', 'is_verified')
