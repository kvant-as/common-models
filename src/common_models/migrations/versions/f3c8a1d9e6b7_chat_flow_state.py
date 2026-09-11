"""add chats.flow_state

Servaces the state machine behind automated widget chat scenarios (e.g.
'org-edit' — changing organisation data via the virtual assistant): the
current step and any values collected so far, kept as a small JSON string.

Revision ID: f3c8a1d9e6b7
Revises: a91e6d4f2b3c
Create Date: 2026-09-18

"""
from alembic import op
import sqlalchemy as sa


revision = "f3c8a1d9e6b7"
down_revision = "a91e6d4f2b3c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chats", schema=None) as batch_op:
        batch_op.add_column(sa.Column("flow_state", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("chats", schema=None) as batch_op:
        batch_op.drop_column("flow_state")
