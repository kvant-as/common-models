"""organization: data from EGR (egr.gov.by) — short name, legal address, status

Revision ID: 7a1e9c2b4d60
Revises: c5d6e7f8a9b0
Create Date: 2026-11-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7a1e9c2b4d60'
down_revision = 'c5d6e7f8a9b0'
branch_labels = None
depends_on = None


def upgrade():
    # Все колонки nullable — заполняются только по кнопке «Обновить из ЕГР»
    # (enPlans), существующие строки и erespondentN не затрагиваются.
    op.add_column('organization', sa.Column('short_name', sa.String(length=255), nullable=True))
    op.add_column('organization', sa.Column('legal_address', sa.String(length=500), nullable=True))
    op.add_column('organization', sa.Column('egr_status', sa.String(length=100), nullable=True))
    op.add_column('organization', sa.Column('egr_status_kind', sa.String(length=20), nullable=True))
    op.add_column('organization', sa.Column('egr_checked_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('organization', 'egr_checked_at')
    op.drop_column('organization', 'egr_status_kind')
    op.drop_column('organization', 'egr_status')
    op.drop_column('organization', 'legal_address')
    op.drop_column('organization', 'short_name')
