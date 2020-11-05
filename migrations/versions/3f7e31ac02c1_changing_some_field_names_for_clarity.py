"""changing some field names for clarity

Revision ID: 3f7e31ac02c1
Revises: 5a0a0d011948
Create Date: 2020-10-29 21:34:13.500945

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '3f7e31ac02c1'
down_revision = '5a0a0d011948'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('gsmodelapp', sa.Column('application_id', sa.Integer(), nullable=True))
    op.drop_constraint('gsmodelapp_ibfk_1', 'gsmodelapp', type_='foreignkey')
    op.create_foreign_key(None, 'gsmodelapp', 'application', ['application_id'], ['id'])
    op.drop_column('gsmodelapp', 'app_id')
    op.add_column('gsmodelnet', sa.Column('network_id', sa.Integer(), nullable=True))
    op.drop_constraint('gsmodelnet_ibfk_2', 'gsmodelnet', type_='foreignkey')
    op.create_foreign_key(None, 'gsmodelnet', 'network', ['network_id'], ['id'])
    op.drop_column('gsmodelnet', 'net_id')
    op.add_column('gsmodelsys', sa.Column('system_id', sa.Integer(), nullable=True))
    op.drop_constraint('gsmodelsys_ibfk_2', 'gsmodelsys', type_='foreignkey')
    op.create_foreign_key(None, 'gsmodelsys', 'system', ['system_id'], ['id'])
    op.drop_column('gsmodelsys', 'sys_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('gsmodelsys', sa.Column('sys_id', mysql.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'gsmodelsys', type_='foreignkey')
    op.create_foreign_key('gsmodelsys_ibfk_2', 'gsmodelsys', 'system', ['sys_id'], ['id'])
    op.drop_column('gsmodelsys', 'system_id')
    op.add_column('gsmodelnet', sa.Column('net_id', mysql.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'gsmodelnet', type_='foreignkey')
    op.create_foreign_key('gsmodelnet_ibfk_2', 'gsmodelnet', 'network', ['net_id'], ['id'])
    op.drop_column('gsmodelnet', 'network_id')
    op.add_column('gsmodelapp', sa.Column('app_id', mysql.INTEGER(), autoincrement=False, nullable=True))
    op.drop_constraint(None, 'gsmodelapp', type_='foreignkey')
    op.create_foreign_key('gsmodelapp_ibfk_1', 'gsmodelapp', 'application', ['app_id'], ['id'])
    op.drop_column('gsmodelapp', 'application_id')
    # ### end Alembic commands ###