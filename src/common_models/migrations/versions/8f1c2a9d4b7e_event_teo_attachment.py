"""event teo attachment

Revision ID: 8f1c2a9d4b7e
Revises: 6daa9f84fc53
Create Date: 2026-10-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8f1c2a9d4b7e'
down_revision = '6daa9f84fc53'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('events', sa.Column('teo_filename', sa.String(length=255), nullable=True))
    op.add_column('events', sa.Column('teo_original_name', sa.String(length=400), nullable=True))
    op.add_column('events', sa.Column('teo_uploaded_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('events', 'teo_uploaded_at')
    op.drop_column('events', 'teo_original_name')
    op.drop_column('events', 'teo_filename')
