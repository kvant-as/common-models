"""plan_approval_paths.stage — номер этапа внутри цикла отправки

Этап 1 — организация-разработчик (исполнитель → руководитель подразделения →
руководитель организации, итоговая подпись ЭЦП), этапы 2..N — организации
маршрута по порядку. Подэтапы (внутренние действия внутри организации)
имеют тот же stage, что и их основной (итоговый) шаг.

Revision ID: 8b2f4d1a6c90
Revises: 7a1e9c2b4d60
"""
from alembic import op
import sqlalchemy as sa

revision = '8b2f4d1a6c90'
down_revision = '7a1e9c2b4d60'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('plan_approval_paths', sa.Column('stage', sa.Integer(), nullable=True))

    # Внутренняя цепочка организации-разработчика (направил / подписал /
    # вернул) — этап 1.
    op.execute("""
        UPDATE plan_approval_paths SET stage = 1
        WHERE is_internal AND (log_action IS NULL OR log_action = 'internal_returned')
          AND step_type <> 'rework'
    """)
    # Внешние организации — 2, 3, ... по порядку в своём цикле.
    op.execute("""
        UPDATE plan_approval_paths p SET stage = r.rn + 1
        FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY plan_id, cycle ORDER BY step_order) AS rn
            FROM plan_approval_paths WHERE NOT is_internal
        ) r
        WHERE p.id = r.id
    """)
    # «Шаг 2» внутри внешней организации — этап своей организации.
    op.execute("""
        UPDATE plan_approval_paths s SET stage = p.stage
        FROM plan_approval_paths p
        WHERE s.is_internal AND s.log_action IS NOT NULL
          AND s.log_action NOT IN ('internal_returned', 'sent_to_rework')
          AND NOT p.is_internal AND p.plan_id = s.plan_id
          AND p.cycle = s.cycle AND p.step_order = s.step_order
    """)


def downgrade():
    op.drop_column('plan_approval_paths', 'stage')
