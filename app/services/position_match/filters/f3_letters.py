"""MF-5 F3 — jyutping letter slot constraints (rhyme/syllable/initial_letters)."""
from __future__ import annotations

def slot_constraint_matches(word, slot, db) -> bool:
    from app.services.jyutping_anchor import matches_jyutping_anchor_at_position

    if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
        return matches_jyutping_anchor_at_position(
            word, slot.pos, slot.kind, str(slot.value or ""), db
        )
    return False
