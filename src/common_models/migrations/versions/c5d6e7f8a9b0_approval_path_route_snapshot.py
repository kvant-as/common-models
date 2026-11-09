"""plan approval path route_snapshot (route of a returned internal attempt)

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-11-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c5d6e7f8a9b0'
down_revision = 'b4c5d6e7f8a9'
branch_labels = None
depends_on = None


def upgrade():
    # Маршрут внешнего согласования ("step_type:org_id,..."), выбранный для
    # попытки, которую вернули на внутреннюю доработку ещё до отправки —
    # заполняется только у строки возврата (log_action='internal_returned'),
    # чтобы «Подписи» показывали, куда план должен был пойти.
    op.add_column('plan_approval_paths', sa.Column('route_snapshot', sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column('plan_approval_paths', 'route_snapshot')
