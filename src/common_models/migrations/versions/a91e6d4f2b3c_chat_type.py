"""add chats.chat_type

Marks which topic a chat was started under in the virtual-assistant widget
('no-org' / 'compl-plan' / 'dif'). 'dif' ("Другое") routes to a human admin
instead of the AI backend and surfaces the chat in the admin panel.

Revision ID: a91e6d4f2b3c
Revises: c776c34b880a
Create Date: 2026-09-18

"""
from alembic import op
import sqlalchemy as sa


revision = "a91e6d4f2b3c"
down_revision = "c776c34b880a"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chats", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chat_type", sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table("chats", schema=None) as batch_op:
        batch_op.drop_column("chat_type")
