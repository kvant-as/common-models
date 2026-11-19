"""Порядок строк раздела отчёта (erespondentN)

Пользователь может перетаскиванием менять порядок строк продукции внутри
раздела отчёта; порядок хранится в sections.sort_order. Существующие строки
получают NULL — для них сохраняется прежний порядок (новые сверху).

Revision ID: a1d3f5b7c9e2
Revises: 9c3e5a7b1d24
"""
from alembic import op
import sqlalchemy as sa

revision = 'a1d3f5b7c9e2'
down_revision = '9c3e5a7b1d24'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sections', sa.Column('sort_order', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('sections', 'sort_order')
