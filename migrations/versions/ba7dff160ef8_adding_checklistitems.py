"""adding checklistitems

Revision ID: ba7dff160ef8
Revises: 7afdef308831
Create Date: 2020-11-02 15:44:49.643665

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ba7dff160ef8'
down_revision = '7afdef308831'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('checklistitem',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('checklist_id', sa.Integer(), nullable=True),
    sa.Column('requirement_id', sa.Integer(), nullable=True),
    sa.Column('implementation_decision', sa.Enum('NA', 'YES', 'PART', 'NO', name='implementationdecision'), nullable=True),
    sa.Column('responsible', sa.Integer(), nullable=True),
    sa.Column('comments', sa.Text(), nullable=True),
    sa.Column('est_amount', sa.Float(), nullable=True),
    sa.Column('target_date', sa.Date(), nullable=True),
    sa.Column('implementation_status', sa.Enum('OPEN', 'WIP', 'DONE', name='implementationstatus'), nullable=True),
    sa.ForeignKeyConstraint(['checklist_id'], ['checklist.id'], ),
    sa.ForeignKeyConstraint(['requirement_id'], ['requirement.id'], ),
    sa.ForeignKeyConstraint(['responsible'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('checklistitem')
    # ### end Alembic commands ###
