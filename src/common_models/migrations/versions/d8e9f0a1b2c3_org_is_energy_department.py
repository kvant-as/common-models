"""organization is_energy_department flag

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-11-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = 'c7d8e9f0a1b2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'organization',
        sa.Column('is_energy_department', sa.Boolean(), server_default='false', nullable=True),
    )


def downgrade():
    op.drop_column('organization', 'is_energy_department')
