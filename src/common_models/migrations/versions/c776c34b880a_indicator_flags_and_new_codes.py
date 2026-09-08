"""indicator flags and new codes

Renumbers Indicator.code for the fuel-type rows (part 1 of the plan)
to match the "КОДЫ строк для enPlans" reference table, and replaces
several hardcoded-by-code checks scattered across the app (which
column) with three explicit flag columns on Indicator:

- is_computed:      value is calculated by update_plan_indicators()
                     and must not be manually added/edited/deleted
                     (replaces the old immutableCodes list in
                     indicator-calc.js).
- higher_is_better: whether a positive difference vs. the imported
                     statistics report should be shown as favorable
                     (green) or not (red) — replaces specialCodes in
                     indicator-calc.js; for group 1 (fuel types) it's
                     backfilled from the existing is_local flag,
                     which drove this exact behavior before.
- is_custom:        "прочие" rows where the user must pick a fuel
                     category and type a custom name, and where more
                     than one instance may be added to a plan
                     (replaces the '2023'/'2024' checks in
                     plan_bp.py and indicator-calc.js).

Revision ID: c776c34b880a
Revises: 2ff307da7ca1
Create Date: 2026-09-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c776c34b880a'
down_revision = '2ff307da7ca1'
branch_labels = None
depends_on = None

# Старый код -> новый код (см. таблицу "КОДЫ строк для enPlans").
# Электро-/тепло-энергия, целевые показатели и итоговые 9xxx-коды в
# таблице не упоминались, поэтому не переименовываются.
CODE_RENAMES = {
    '1000': '1101',
    '2000': '1090',
    '2001': '1050',
    '2002': '1040',
    '2003': '1660',
    '2004': '1075',
    '2005': '1160',
    '2006': '1150',
    '2007': '1060',
    '2008': '1750',
    '2009': '1790',
    '2010': '1110',
    '2011': '1620',
    '2025': '1630',
    '2012': '1640',
    '2013': '1794',
    '2014': '1745',
    '2015': '1690',
    '2016': '1680',
    '2017': '1742',
    '2018': '1744',
    '2019': '1785',
    '2020': '1730',
    '2021': '1740',
    '2022': '1780',
    '2023': '1710',
    '2024': '1700',
}

# Коды (уже новые, где применимо), для которых показатель считается
# автоматически и не должен удаляться/редактироваться вручную —
# см. update_plan_indicators() в website/utils/plans.py.
COMPUTED_CODES = ['260', '9900', '9999', '1101', '1797', '1796', '9915', '9916', '9917', '9910']

# Коды, для которых рост значения относительно отчёта — это хорошо
# (доля местных/возобновляемых ТЭР). Для группы 1 (виды топлива)
# этот же смысл несёт is_local — заполняется отдельным запросом ниже.
HIGHER_IS_BETTER_CODES = ['1796', '1797', '9916', '9917', '1425', '1424']

# "Прочие" категории — требуют выбора категории топлива и своего
# наименования, и таких можно добавить в план несколько.
CUSTOM_CODES = ['1710', '1700']


def upgrade():
    op.add_column('indicators', sa.Column('is_computed', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('indicators', sa.Column('higher_is_better', sa.Boolean(), nullable=True))
    op.add_column('indicators', sa.Column('is_custom', sa.Boolean(), nullable=False, server_default=sa.false()))

    connection = op.get_bind()

    for old_code, new_code in CODE_RENAMES.items():
        connection.execute(
            sa.text('UPDATE indicators SET code = :new_code WHERE code = :old_code'),
            {'new_code': new_code, 'old_code': old_code}
        )

    # Группа 1 (виды топлива) — раньше цвет разницы определялся по
    # is_local напрямую, теперь через higher_is_better той же строки.
    connection.execute(sa.text('UPDATE indicators SET higher_is_better = is_local WHERE "Group" = 1'))

    connection.execute(
        sa.text('UPDATE indicators SET higher_is_better = true WHERE code = ANY(:codes)'),
        {'codes': HIGHER_IS_BETTER_CODES}
    )
    connection.execute(
        sa.text('UPDATE indicators SET is_computed = true WHERE code = ANY(:codes)'),
        {'codes': COMPUTED_CODES}
    )
    connection.execute(
        sa.text('UPDATE indicators SET is_custom = true WHERE code = ANY(:codes)'),
        {'codes': CUSTOM_CODES}
    )


def downgrade():
    connection = op.get_bind()

    for old_code, new_code in CODE_RENAMES.items():
        connection.execute(
            sa.text('UPDATE indicators SET code = :old_code WHERE code = :new_code'),
            {'old_code': old_code, 'new_code': new_code}
        )

    op.drop_column('indicators', 'is_custom')
    op.drop_column('indicators', 'higher_is_better')
    op.drop_column('indicators', 'is_computed')
