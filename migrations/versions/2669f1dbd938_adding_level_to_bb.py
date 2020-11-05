"""adding level to BB

Revision ID: 2669f1dbd938
Revises: 16e1a1fcdacd
Create Date: 2020-10-27 15:31:31.706875

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2669f1dbd938'
down_revision = '16e1a1fcdacd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('buildingblock', sa.Column('level', sa.Enum('BASE', 'STANDARD', 'HIGH', name='protectionlevel'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('buildingblock', 'level')
    # ### end Alembic commands ###
