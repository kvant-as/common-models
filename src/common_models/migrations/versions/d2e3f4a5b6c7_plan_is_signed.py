"""simplify internal_status to is_signed bool

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plans', sa.Column('is_signed', sa.Boolean(), nullable=False, server_default='false'))
    # internal_status='signed' -> is_signed=True, до удаления колонки
    op.execute("UPDATE plans SET is_signed = true WHERE internal_status = 'signed'")
    op.drop_column('plans', 'internal_status')


def downgrade():
    op.add_column('plans', sa.Column('internal_status', sa.String(length=20), nullable=True))
    op.execute("""
        UPDATE plans SET internal_status = CASE
            WHEN is_signed THEN 'signed'
            WHEN pending_signer_user_id IS NOT NULL THEN 'pending_signature'
            ELSE NULL
        END
    """)
    op.drop_column('plans', 'is_signed')
