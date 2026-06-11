"""word_relations: canonical min-id ordering + (word_id, related_id, relation_type) unique

Revision ID: 20260611_2330
Revises: 20260611_2200
Create Date: 2026-06-11
"""

from alembic import op

revision = "20260611_2330"
down_revision = "20260611_2200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM word_relations WHERE word_id > related_id")
    op.execute("""
        DELETE FROM word_relations wr
        WHERE wr.id NOT IN (
            SELECT MIN(id) FROM word_relations
            GROUP BY word_id, related_id, relation_type
        )
    """)
    op.drop_constraint("uq_word_relation_pair", "word_relations", type_="unique")
    op.create_unique_constraint(
        "uq_word_relation",
        "word_relations",
        ["word_id", "related_id", "relation_type"],
    )


def downgrade() -> None:
    op.execute("""
        DELETE FROM word_relations wr
        WHERE wr.id NOT IN (
            SELECT MIN(id) FROM word_relations GROUP BY word_id, related_id
        )
    """)
    op.drop_constraint("uq_word_relation", "word_relations", type_="unique")
    op.create_unique_constraint(
        "uq_word_relation_pair",
        "word_relations",
        ["word_id", "related_id"],
    )
