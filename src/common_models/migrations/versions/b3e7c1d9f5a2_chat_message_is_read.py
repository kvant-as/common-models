"""Прочитано ли сообщение чата администратором

chat_messages.is_read — для обращений «Другое» (чаты поддержки enPlans):
сообщение пользователя считается прочитанным, когда администратор открыл
переписку. Для уже существующих данных: всё прочитано, кроме сообщений
пользователя в чатах поддержки после последнего ответа администратора —
это обращения, которые ждут ответа.

Revision ID: b3e7c1d9f5a2
Revises: a8d2f4b6c1e9
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3e7c1d9f5a2'
down_revision = 'a8d2f4b6c1e9'
branch_labels = None
depends_on = None

SUPPORT_CHAT_TYPE = 'dif'


def upgrade():
    op.add_column('chat_messages', sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE chat_messages SET is_read = true")
    op.execute(sa.text("""
        UPDATE chat_messages AS m
        SET is_read = false
        FROM chats AS c
        WHERE m.chat_id = c.id
          AND c.chat_type = :support
          AND m.is_user = true
          AND m.created_at > COALESCE(
              (SELECT max(a.created_at) FROM chat_messages AS a
               WHERE a.chat_id = m.chat_id AND a.is_user = false),
              '-infinity'::timestamp)
    """).bindparams(support=SUPPORT_CHAT_TYPE))
    op.create_index('ix_chat_messages_unread', 'chat_messages', ['chat_id'],
                    postgresql_where=sa.text('is_read = false AND is_user = true'))


def downgrade():
    op.drop_index('ix_chat_messages_unread', table_name='chat_messages')
    op.drop_column('chat_messages', 'is_read')
