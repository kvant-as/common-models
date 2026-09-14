"""add organization.created_at

Needed to compute an honest "+N this month" trend on the enPlans landing
page (website/routes/views.py: begin_page) — previously that figure was a
hardcoded string, and Organization had no timestamp to derive it from.
Existing rows get NULL (unknown creation date, correctly excluded from any
"created this month" count); new rows get it from the ORM-side default.

Revision ID: b2e7f4a1c9d3
Revises: f3c8a1d9e6b7
Create Date: 2026-09-16

"""
from alembic import op
import sqlalchemy as sa


revision = "b2e7f4a1c9d3"
down_revision = "f3c8a1d9e6b7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("organization", schema=None) as batch_op:
        batch_op.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("organization", schema=None) as batch_op:
        batch_op.drop_column("created_at")
