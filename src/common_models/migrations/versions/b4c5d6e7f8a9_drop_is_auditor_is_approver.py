"""drop User.is_auditor/is_approver columns (replaced by Organization flags)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b4c5d6e7f8a9'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    # Ни enPlans, ни erespondentN больше не читают эти колонки — обе
    # согласующая/утверждающая принадлежность читается прямо из
    # Organization.is_coordinator/is_region_management/is_approver (см.
    # User.has_auditor_access/has_approver_access/is_region_auditor),
    # не с самого пользователя.
    op.drop_column('user', 'is_auditor')
    op.drop_column('user', 'is_approver')


def downgrade():
    op.add_column('user', sa.Column('is_auditor', sa.Boolean(), server_default='false'))
    op.add_column('user', sa.Column('is_approver', sa.Boolean(), server_default='false'))
