"""add user_app_activity

Revision ID: f3a9c1b47e20
Revises: 9c35ff2f0fb4
Create Date: 2026-08-31

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a9c1b47e20'
down_revision = '9c35ff2f0fb4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_app_activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('app', sa.String(length=32), nullable=False),
        sa.Column('first_seen', sa.DateTime(), nullable=False),
        sa.Column('last_active', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'app', name='uq_user_app_activity'),
    )


def downgrade():
    op.drop_table('user_app_activity')
