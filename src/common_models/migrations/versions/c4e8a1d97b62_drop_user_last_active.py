"""drop user.last_active

Per-app activity is now the single source of truth: ``UserAppActivity.last_active``
for ``(user_id, app)``. The global ``user.last_active`` column is removed.

Revision ID: c4e8a1d97b62
Revises: f3a9c1b47e20
Create Date: 2026-09-01

"""
from alembic import op
import sqlalchemy as sa


revision = "c4e8a1d97b62"
down_revision = "f3a9c1b47e20"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("last_active")


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("last_active", sa.DateTime(), nullable=True))
