"""word_relations: add group_codes for Cilin hierarchy sort

Revision ID: 20260612_1200
Revises: 20260611_2330
Create Date: 2026-06-12
"""

from alembic import op
import sqlalchemy as sa

revision = "20260612_1200"
down_revision = "20260611_2330"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("word_relations", sa.Column("group_codes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("word_relations", "group_codes")
