"""drop User.is_admin/is_reader columns (replaced by Role/user_roles)

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-11-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3b4c5d6e7f8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    # user_roles уже содержит 'admin'/'reader' для всех, у кого был
    # выставлен is_admin/is_reader (бэкфилл сделан в f2a3b4c5d6e7) —
    # сами колонки теперь нигде не читаются (enPlans и erespondentN обе
    # переведены на User.is_admin/is_reader как свойства над user_roles).
    op.drop_column('user', 'is_admin')
    op.drop_column('user', 'is_reader')


def downgrade():
    op.add_column('user', sa.Column('is_admin', sa.Boolean(), server_default='false'))
    op.add_column('user', sa.Column('is_reader', sa.Boolean(), server_default='false'))

    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE "user" SET is_admin = true WHERE id IN (
            SELECT ur.user_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE r.code = 'admin'
        )
    """))
    bind.execute(sa.text("""
        UPDATE "user" SET is_reader = true WHERE id IN (
            SELECT ur.user_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id WHERE r.code = 'reader'
        )
    """))
