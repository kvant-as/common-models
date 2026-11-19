"""Новости привязаны к приложению через application_id

Вместо двух флагов is_erespondentn / is_enplans новость, как и
пользователь, принадлежит одному приложению (applications.id). Новость,
отмеченная для обоих приложений, копируется: по одной на каждое
приложение. Новость без отметок относится к erespondentN (прежнее
значение по умолчанию).

Revision ID: c4f8a2e6b9d3
Revises: b7e2c4d6f8a1
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4f8a2e6b9d3'
down_revision = 'b7e2c4d6f8a1'
branch_labels = None
depends_on = None

COPY_COLUMNS = 'title, text, img_name, is_published, published_at, views_count, created_time'


def upgrade():
    bind = op.get_bind()
    op.add_column('news', sa.Column('application_id', sa.Integer(), nullable=True))

    apps = dict(bind.execute(sa.text('select code, id from applications')).all())
    er_id, en_id = apps.get('erespondentn'), apps.get('enplans')
    if er_id is None or en_id is None:
        raise RuntimeError('В таблице applications нет записей erespondentn и enplans')

    bind.execute(sa.text(f"""
        insert into news ({COPY_COLUMNS}, application_id)
        select {COPY_COLUMNS}, :en from news
        where is_erespondentn is true and is_enplans is true
    """), {'en': en_id})
    bind.execute(sa.text("""
        update news set application_id = case
            when is_erespondentn is true then :er
            when is_enplans is true then :en
            else :er end
        where application_id is null
    """), {'er': er_id, 'en': en_id})

    op.alter_column('news', 'application_id', nullable=False)
    op.create_foreign_key('fk_news_application_id', 'news', 'applications', ['application_id'], ['id'])
    op.create_index('ix_news_application_id', 'news', ['application_id'])
    op.drop_column('news', 'is_erespondentn')
    op.drop_column('news', 'is_enplans')


def downgrade():
    bind = op.get_bind()
    op.add_column('news', sa.Column('is_erespondentn', sa.Boolean(), nullable=True))
    op.add_column('news', sa.Column('is_enplans', sa.Boolean(), nullable=True))
    bind.execute(sa.text("""
        update news set
            is_erespondentn = (application_id = (select id from applications where code = 'erespondentn')),
            is_enplans = (application_id = (select id from applications where code = 'enplans'))
    """))
    op.drop_index('ix_news_application_id', table_name='news')
    op.drop_constraint('fk_news_application_id', 'news', type_='foreignkey')
    op.drop_column('news', 'application_id')
