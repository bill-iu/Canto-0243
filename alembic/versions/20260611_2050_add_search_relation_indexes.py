"""add search and relation indexes

Revision ID: 20260611_2050
Revises:
Create Date: 2026-06-11
"""

from alembic import op
import sqlalchemy as sa

revision = "20260611_2050"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("idx_length_code", "words", ["length", "code"], if_not_exists=True)
    op.create_index("idx_length_code_finals", "words", ["length", "code", "finals"], if_not_exists=True)

    op.create_table(
        "word_relations",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("word_id", sa.BigInteger(), nullable=False),
        sa.Column("related_id", sa.BigInteger(), nullable=False),
        sa.Column("relation_type", sa.String(length=16), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"]),
        sa.ForeignKeyConstraint(["related_id"], ["words.id"]),
        sa.UniqueConstraint("word_id", "related_id", "relation_type", name="uq_word_relation"),
        if_not_exists=True,
    )
    op.create_index("idx_word_rel_word_type", "word_relations", ["word_id", "relation_type"], if_not_exists=True)
    op.create_index("idx_word_rel_related_type", "word_relations", ["related_id", "relation_type"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_word_rel_related_type", table_name="word_relations", if_exists=True)
    op.drop_index("idx_word_rel_word_type", table_name="word_relations", if_exists=True)
    op.drop_table("word_relations", if_exists=True)
    op.drop_index("idx_length_code_finals", table_name="words", if_exists=True)
    op.drop_index("idx_length_code", table_name="words", if_exists=True)
