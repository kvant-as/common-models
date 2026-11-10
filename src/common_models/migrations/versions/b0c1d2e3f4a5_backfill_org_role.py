"""backfill org_role for existing accounts

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-10-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b0c1d2e3f4a5'
down_revision = 'a9b0c1d2e3f4'
branch_labels = None
depends_on = None


def upgrade():
    # org_role появился только что и проставляется автоматически лишь при
    # НОВОЙ регистрации (website.user.add_param). У всех существующих
    # аккаунтов организаций-разработчиков до сих пор был ровно один аккаунт
    # на организацию — то есть он и есть её фактический руководитель.
    # Аккаунты-аудиторы/утверждающие/админы/читатели не затрагиваем — у них
    # org_role не используется.
    op.execute("""
        UPDATE "user"
        SET org_role = 'org_head'
        WHERE org_role IS NULL
          AND organization_id IS NOT NULL
          AND is_admin = false
          AND is_auditor = false
          AND is_approver = false
          AND is_reader = false
    """)


def downgrade():
    op.execute("""
        UPDATE "user"
        SET org_role = NULL
        WHERE org_role = 'org_head'
    """)
