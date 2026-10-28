"""plan ticket approval path link

Revision ID: d6e7f8a9b0c1
Revises: c4d5e6f7a8b9
Create Date: 2026-10-28 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd6e7f8a9b0c1'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('Plan_tickets', sa.Column('approval_path_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_plan_tickets_approval_path_id',
        'Plan_tickets', 'plan_approval_paths',
        ['approval_path_id'], ['id'],
    )


def downgrade():
    op.drop_constraint('fk_plan_tickets_approval_path_id', 'Plan_tickets', type_='foreignkey')
    op.drop_column('Plan_tickets', 'approval_path_id')
