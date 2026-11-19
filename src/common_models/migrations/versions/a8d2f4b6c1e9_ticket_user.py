"""Автор квитанции отчёта

ticket.user_id — пользователь, который оставил квитанцию: проверяющий для
решения проверки, сотрудник организации для отмены отправки. У старых
квитанций автор неизвестен (NULL).

Revision ID: a8d2f4b6c1e9
Revises: d5a9c1e3f7b2
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8d2f4b6c1e9'
down_revision = 'd5a9c1e3f7b2'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('ticket', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_ticket_user_id', 'ticket', 'user', ['user_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_ticket_user_id', 'ticket', ['user_id'])


def downgrade():
    op.drop_index('ix_ticket_user_id', table_name='ticket')
    op.drop_constraint('fk_ticket_user_id', 'ticket', type_='foreignkey')
    op.drop_column('ticket', 'user_id')
