"""merge prompt and search heads

Revision ID: a74e77d46737
Revises: add_prompt_model, search_indexes
Create Date: 2025-08-07 15:14:33.015027

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a74e77d46737'
down_revision = ('add_prompt_model', 'search_indexes')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
