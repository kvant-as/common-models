"""widen news.img_name to 255

Cover-image file names (uploaded from the admin) easily exceed the old
20-char limit.

Revision ID: d2f6b8c1a473
Revises: c4e8a1d97b62
Create Date: 2026-09-01

"""
from alembic import op
import sqlalchemy as sa


revision = "d2f6b8c1a473"
down_revision = "c4e8a1d97b62"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("news", schema=None) as batch_op:
        batch_op.alter_column(
            "img_name",
            existing_type=sa.String(length=20),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade():
    with op.batch_alter_table("news", schema=None) as batch_op:
        batch_op.alter_column(
            "img_name",
            existing_type=sa.String(length=255),
            type_=sa.String(length=20),
            existing_nullable=True,
        )
