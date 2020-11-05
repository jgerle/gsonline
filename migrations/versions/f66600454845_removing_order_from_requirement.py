"""removing order from requirement

Revision ID: f66600454845
Revises: 1e5c68b75c13
Create Date: 2020-10-27 17:26:56.718969

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'f66600454845'
down_revision = '1e5c68b75c13'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('requirement', 'order')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('requirement', sa.Column('order', mysql.VARCHAR(length=10), nullable=True))
    # ### end Alembic commands ###
