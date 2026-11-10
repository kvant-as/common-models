"""roles table + user_roles — replaces User.org_role column

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-11-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f2a3b4c5d6e7'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None

ROLE_CATALOG = [
    # (code, label, is_org_role)
    ('admin', 'Администратор', False),
    ('reader', 'Читатель', False),
    ('executor', 'Исполнитель', True),
    ('dept_head', 'Руководитель структурного подразделения', True),
    ('org_head', 'Руководитель организации', True),
    ('org_head_deputy', 'Заместитель руководителя организации', True),
]


def upgrade():
    roles_table = op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('is_org_role', sa.Boolean(), nullable=False, server_default='false'),
        sa.UniqueConstraint('code', name='uq_roles_code'),
    )
    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), primary_key=True),
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id'), primary_key=True),
    )

    op.bulk_insert(roles_table, [
        {'code': code, 'label': label, 'is_org_role': is_org_role}
        for code, label, is_org_role in ROLE_CATALOG
    ])

    bind = op.get_bind()

    # Бэкфилл user_roles из уже существующих данных ДО удаления колонок —
    # is_admin/is_reader (остаются в User как есть, см. models.py) и
    # org_role (колонка удаляется ниже, замещается User.org_role —
    # computed property поверх этой же таблицы user_roles).
    role_ids = {code: rid for rid, code in bind.execute(
        sa.text("SELECT id, code FROM roles")
    ).fetchall()}

    for code in ('executor', 'dept_head', 'org_head', 'org_head_deputy'):
        bind.execute(sa.text(
            "INSERT INTO user_roles (user_id, role_id) "
            "SELECT id, :role_id FROM \"user\" WHERE org_role = :code"
        ), {'role_id': role_ids[code], 'code': code})

    bind.execute(sa.text(
        "INSERT INTO user_roles (user_id, role_id) "
        "SELECT id, :role_id FROM \"user\" WHERE is_admin = true"
    ), {'role_id': role_ids['admin']})
    bind.execute(sa.text(
        "INSERT INTO user_roles (user_id, role_id) "
        "SELECT id, :role_id FROM \"user\" WHERE is_reader = true"
    ), {'role_id': role_ids['reader']})

    op.drop_column('user', 'org_role')


def downgrade():
    op.add_column('user', sa.Column('org_role', sa.String(length=30), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT ur.user_id, r.code FROM user_roles ur "
        "JOIN roles r ON r.id = ur.role_id WHERE r.is_org_role = true"
    )).fetchall()
    for user_id, code in rows:
        bind.execute(sa.text("UPDATE \"user\" SET org_role = :code WHERE id = :uid"), {'code': code, 'uid': user_id})

    op.drop_table('user_roles')
    op.drop_table('roles')
