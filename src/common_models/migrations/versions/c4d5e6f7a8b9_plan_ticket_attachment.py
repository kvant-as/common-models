"""plan ticket attachment

Revision ID: c4d5e6f7a8b9
Revises: a8b9c0d1e2f3
Create Date: 2026-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'a8b9c0d1e2f3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('Plan_tickets', sa.Column('attachment_filename', sa.String(length=255), nullable=True))
    op.add_column('Plan_tickets', sa.Column('attachment_original_name', sa.String(length=400), nullable=True))
    op.add_column('Plan_tickets', sa.Column('attachment_uploaded_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('Plan_tickets', 'attachment_uploaded_at')
    op.drop_column('Plan_tickets', 'attachment_original_name')
    op.drop_column('Plan_tickets', 'attachment_filename')
