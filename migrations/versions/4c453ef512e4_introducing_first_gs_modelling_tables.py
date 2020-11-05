"""Introducing first GS modelling tables

Revision ID: 4c453ef512e4
Revises: 32d44da5a47c
Create Date: 2020-10-29 11:16:00.395726

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c453ef512e4'
down_revision = '32d44da5a47c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('gsmodelbase',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('bb_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=50), nullable=True),
    sa.Column('implementation_decision', sa.Enum('NA', 'YES', 'PART', 'NO', name='implementationdecision'), nullable=True),
    sa.Column('responsible', sa.Integer(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('est_amount', sa.Float(), nullable=True),
    sa.Column('target_date', sa.Date(), nullable=True),
    sa.Column('implementation_status', sa.Enum('OPEN', 'WIP', 'DONE', name='implementationstatus'), nullable=True),
    sa.ForeignKeyConstraint(['bb_id'], ['buildingblock.id'], ),
    sa.ForeignKeyConstraint(['responsible'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('gsmodeldom',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dom_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['dom_id'], ['infodomain.id'], ),
    sa.ForeignKeyConstraint(['id'], ['gsmodelbase.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('gsmodeldom')
    op.drop_table('gsmodelbase')
    # ### end Alembic commands ###
