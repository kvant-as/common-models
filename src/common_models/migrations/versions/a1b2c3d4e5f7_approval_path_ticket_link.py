"""plan approval path ticket link, drop remark and ticket luck

Revision ID: a1b2c3d4e5f7
Revises: f0a1b2c3d4e5
Create Date: 2026-11-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f7'
down_revision = 'f0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('ticket_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_plan_approval_paths_ticket_id',
        'plan_approval_paths', 'Plan_tickets',
        ['ticket_id'], ['id'],
    )
    op.drop_column('plan_approval_paths', 'remark')
    op.drop_column('Plan_tickets', 'luck')


def downgrade():
    op.add_column('Plan_tickets', sa.Column('luck', sa.Boolean(), nullable=True))
    op.add_column('plan_approval_paths', sa.Column('remark', sa.String(length=500), nullable=True))
    op.drop_constraint('fk_plan_approval_paths_ticket_id', 'plan_approval_paths', type_='foreignkey')
    op.drop_column('plan_approval_paths', 'ticket_id')
