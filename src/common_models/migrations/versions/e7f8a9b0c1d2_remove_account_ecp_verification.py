"""remove account ecp verification

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e7f8a9b0c1d2'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_user_verifications_user_id', table_name='user_verifications')
    op.drop_table('user_verifications')
    op.drop_column('user', 'ecp_verified_until')


def downgrade():
    op.add_column('user', sa.Column('ecp_verified_until', sa.DateTime(), nullable=True))
    op.create_table(
        'user_verifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('cert_subject', sa.String(length=500), nullable=True),
        sa.Column('cert_unp', sa.String(length=20), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
    )
    op.create_index('ix_user_verifications_user_id', 'user_verifications', ['user_id'])
