"""adding column is_active to Requirement

Revision ID: 32d44da5a47c
Revises: e44c7850c9fb
Create Date: 2020-10-29 09:29:24.594823

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '32d44da5a47c'
down_revision = 'e44c7850c9fb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('requirement', sa.Column('is_active', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('requirement', 'is_active')
    # ### end Alembic commands ###
