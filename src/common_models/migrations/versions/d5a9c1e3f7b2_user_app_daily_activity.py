"""Активность пользователей по дням

Таблица user_app_daily_activity — строка на пользователя, приложение и
день; заполняется в touch_user_activity. Для уже существующих данных
заносятся известные дни: день первого визита и день последнего визита из
user_app_activity.

Revision ID: d5a9c1e3f7b2
Revises: c4f8a2e6b9d3
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5a9c1e3f7b2'
down_revision = 'c4f8a2e6b9d3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_app_daily_activity',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('app', sa.String(32), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('ticks', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('first_at', sa.DateTime(), nullable=False),
        sa.Column('last_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('user_id', 'app', 'day', name='uq_user_app_daily_activity'),
    )
    op.create_index('ix_user_app_daily_activity_app_day', 'user_app_daily_activity', ['app', 'day'])

    op.execute("""
        INSERT INTO user_app_daily_activity (user_id, app, day, ticks, first_at, last_at)
        SELECT user_id, app, CAST(first_seen AS date), 1, first_seen, first_seen
        FROM user_app_activity
        WHERE first_seen IS NOT NULL
    """)
    op.execute("""
        INSERT INTO user_app_daily_activity (user_id, app, day, ticks, first_at, last_at)
        SELECT a.user_id, a.app, CAST(a.last_active AS date), 1, a.last_active, a.last_active
        FROM user_app_activity a
        WHERE a.last_active IS NOT NULL
          AND CAST(a.last_active AS date) <> CAST(a.first_seen AS date)
    """)


def downgrade():
    op.drop_index('ix_user_app_daily_activity_app_day', table_name='user_app_daily_activity')
    op.drop_table('user_app_daily_activity')
