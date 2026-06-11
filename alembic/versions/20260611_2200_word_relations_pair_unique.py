"""word_relations unique on (word_id, related_id) only

Revision ID: 20260611_2200
Revises: 20260611_2050
Create Date: 2026-06-11
"""

from alembic import op

revision = "20260611_2200"
down_revision = "20260611_2050"
branch_labels = None
depends_on = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint("uq_word_relation_pair", "word_relations", type_="unique")
    op.create_unique_constraint(
        "uq_word_relation",
        "word_relations",
        ["word_id", "related_id", "relation_type"],
    )
