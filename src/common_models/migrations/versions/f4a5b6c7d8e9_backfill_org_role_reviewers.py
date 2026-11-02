"""backfill org_role for auditor/approver accounts

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-11-02 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    # Оригинальный бэкфилл (b0c1d2e3f4a5) сознательно пропустил
    # аудиторов/утверждающих — org_role им тогда был не нужен. Теперь
    # нужен (см. "Шаг 2" внутреннего подписания — решение согласующей/
    # утверждающей организации тоже подписывает руководитель, а не тот,
    # кто его готовил). В отличие от организаций-разработчиков (там было
    # гарантированно по одному аккаунту на организацию), у этих — могло
    # исторически накопиться несколько аккаунтов на одну organization_id,
    # поэтому бэкфилл не может просто проставить всем 'org_head' — это
    # нарушило бы инвариант "одна роль - один человек на организацию"
    # (see admin.py::_user_on_save, views.invite_employee). Берём самый
    # ранний аккаунт в каждой группе под 'org_head', остальным — 'dept_head'.
    op.execute("""
        WITH ranked AS (
            SELECT id, organization_id,
                   ROW_NUMBER() OVER (PARTITION BY organization_id ORDER BY id) AS rn
            FROM "user"
            WHERE org_role IS NULL
              AND organization_id IS NOT NULL
              AND is_admin = false
              AND is_reader = false
              AND (is_auditor = true OR is_approver = true)
        )
        UPDATE "user"
        SET org_role = CASE WHEN ranked.rn = 1 THEN 'org_head' ELSE 'dept_head' END
        FROM ranked
        WHERE "user".id = ranked.id
    """)


def downgrade():
    op.execute("""
        UPDATE "user"
        SET org_role = NULL
        WHERE (is_auditor = true OR is_approver = true)
          AND org_role IN ('org_head', 'dept_head')
    """)
