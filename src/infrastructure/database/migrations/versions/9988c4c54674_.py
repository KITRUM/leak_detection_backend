"""empty message

Revision ID: 9988c4c54674
Revises: c160adb07d59
Create Date: 2023-07-23 19:14:50.199924

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '9988c4c54674'
down_revision = 'c160adb07d59'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('simulation_detection_rates', sa.Column('rate', sa.Float(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('simulation_detection_rates', 'rate')
    # ### end Alembic commands ###
