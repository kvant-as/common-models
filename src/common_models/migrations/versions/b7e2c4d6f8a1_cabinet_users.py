"""Учётные записи сотрудников личного кабинета (enPlans)

Сотрудников создаёт ответственный за кабинет: вход по логину, своей почты
у сотрудника нет — у организации одна почта (учётная запись,
зарегистрированная с ЭЦП). Добавляются логин, флаг «Ответственный за
кабинет», активность учётной записи, подразделение и справочник
подразделений организации.

Существующие пользователи enPlans получают логин (i.ivanov),
руководители организаций — флаг ответственного за кабинет; у остальных
сотрудников организаций почта снимается.

Revision ID: b7e2c4d6f8a1
Revises: a1d3f5b7c9e2
"""
from alembic import op
import sqlalchemy as sa

revision = 'b7e2c4d6f8a1'
down_revision = 'a1d3f5b7c9e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organization.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('organization_id', 'name', name='uq_department_org_name'),
    )
    op.create_index('ix_departments_organization_id', 'departments', ['organization_id'])

    op.add_column('user', sa.Column('login', sa.String(64), nullable=True))
    op.add_column('user', sa.Column('is_cabinet_owner', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('user', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('user', sa.Column('deactivated_at', sa.DateTime(), nullable=True))
    op.add_column('user', sa.Column('department_id', sa.Integer(),
                                    sa.ForeignKey('departments.id', ondelete='SET NULL'), nullable=True))
    op.create_unique_constraint('uq_user_login_application', 'user', ['login', 'application_id'])

    from common_models.logins import generate_login

    bind = op.get_bind()
    app_id = bind.execute(sa.text("select id from applications where code = 'enplans'")).scalar()
    if app_id is None:
        return

    rows = bind.execute(sa.text("""
        select u.id, u.first_name, u.last_name, u.organization_id,
               exists(select 1 from user_roles ur join roles r on r.id = ur.role_id
                      where ur.user_id = u.id and r.code = 'org_head') as is_head,
               exists(select 1 from user_roles ur join roles r on r.id = ur.role_id
                      where ur.user_id = u.id and r.code = 'admin') as is_admin,
               exists(select 1 from user_roles ur join roles r on r.id = ur.role_id
                      where ur.user_id = u.id and r.is_org_role) as has_org_role
        from "user" u where u.application_id = :app order by u.id
    """), {'app': app_id}).all()

    taken = set()
    for uid, first, last, org_id, is_head, is_admin, has_org_role in rows:
        login = generate_login(first or '', last or f'user{uid}', lambda c: c in taken)
        taken.add(login)
        params = {'id': uid, 'login': login}
        sql = 'update "user" set login = :login'
        if is_head:
            sql += ', is_cabinet_owner = true'
        elif has_org_role and org_id and not is_admin:
            sql += ', email = null'
        bind.execute(sa.text(sql + ' where id = :id'), params)


def downgrade():
    op.drop_constraint('uq_user_login_application', 'user', type_='unique')
    op.drop_column('user', 'department_id')
    op.drop_column('user', 'deactivated_at')
    op.drop_column('user', 'is_active')
    op.drop_column('user', 'is_cabinet_owner')
    op.drop_column('user', 'login')
    op.drop_index('ix_departments_organization_id', table_name='departments')
    op.drop_table('departments')
