"""Департамент по энергоэффективности — согласующая, а не утверждающая

enPlans добавлял Департамент в маршрут (build_approval_chain) с типом этапа
'approver'. Из-за этого на его этапе действовали правила утверждающей
организации (только положительное решение), в «Подписях» он показывался как
«Утверждение», а в экспорте попадал в строку утверждающей организации.
Департамент нельзя выбрать утверждающей (is_approver=False), поэтому все его
этапы с типом 'approver' — следствие этой ошибки: переводим в 'coordinator'.

Revision ID: 9c3e5a7b1d24
Revises: 8b2f4d1a6c90
"""
from alembic import op

revision = '9c3e5a7b1d24'
down_revision = '8b2f4d1a6c90'
branch_labels = None
depends_on = None


def upgrade():
    # Основные этапы и строки внутреннего рассмотрения («Шаг 2»: у них тот
    # же step_type, что у этапа своей организации).
    op.execute("""
        UPDATE plan_approval_paths SET step_type = 'coordinator'
        WHERE step_type = 'approver'
          AND organization_id IN (SELECT id FROM organization WHERE is_energy_department)
    """)
    # Снимки маршрута вернутых попыток: "region:7946,approver:9270,approver:8945".
    op.execute("""
        UPDATE plan_approval_paths p
        SET route_snapshot = regexp_replace(
            p.route_snapshot, '(^|,)approver:' || o.id || '(,|$)', '\\1coordinator:' || o.id || '\\2', 'g')
        FROM organization o
        WHERE o.is_energy_department AND p.route_snapshot IS NOT NULL
          AND p.route_snapshot ~ ('(^|,)approver:' || o.id || '(,|$)')
    """)


def downgrade():
    # Обратно не возвращаем: тип 'approver' у Департамента был ошибкой.
    pass
