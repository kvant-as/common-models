"""user ecp verification

Revision ID: 6daa9f84fc53
Revises: c03f701ee6fc
Create Date: 2026-10-01 11:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6daa9f84fc53'
down_revision = 'c03f701ee6fc'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('ecp_verified_until', sa.DateTime(), nullable=True))

    op.create_table('user_verifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('verified_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('cert_subject', sa.String(length=500), nullable=True),
        sa.Column('cert_unp', sa.String(length=20), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_verifications_user_id'), 'user_verifications', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_user_verifications_user_id'), table_name='user_verifications')
    op.drop_table('user_verifications')
    op.drop_column('user', 'ecp_verified_until')
