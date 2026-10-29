"""applications table and per-application user scoping

Revision ID: a1b2c3d4e5f6
Revises: 8f1c2a9d4b7e
Create Date: 2026-10-23 00:00:00.000000

Adds the Application table (erespondentN / enPlans, one row each) and scopes
User accounts to a single application: email is no longer globally unique,
only unique per (email, application_id) — the same person now registers a
separate account in each application.

Existing user rows are left with application_id = NULL by this migration on
purpose: erespondentN backfills its own historical rows via an admin-panel
action (see website/admin.py there), enPlans starts clean (one admin created
manually, everyone else registers fresh and gets application_id stamped at
registration). Until backfilled, rows with application_id IS NULL are not
constrained against each other by the new unique index (Postgres treats NULL
as distinct in a unique constraint) — that's an acceptable, temporary gap
during the migration window, not a steady state.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8f1c2a9d4b7e'
branch_labels = None
depends_on = None

applications_table = sa.table(
    'applications',
    sa.column('code', sa.String),
    sa.column('name', sa.String),
)


def upgrade():
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )

    op.bulk_insert(applications_table, [
        {'code': 'erespondentn', 'name': 'erespondentN'},
        {'code': 'enplans', 'name': 'enPlans'},
    ])

    op.add_column('user', sa.Column('application_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_user_application_id', 'user', 'applications',
        ['application_id'], ['id']
    )

    op.drop_constraint('user_email_key', 'user', type_='unique')
    op.create_unique_constraint('uq_user_email_application', 'user', ['email', 'application_id'])


def downgrade():
    op.drop_constraint('uq_user_email_application', 'user', type_='unique')
    op.create_unique_constraint('user_email_key', 'user', ['email'])

    op.drop_constraint('fk_user_application_id', 'user', type_='foreignkey')
    op.drop_column('user', 'application_id')

    op.drop_table('applications')
