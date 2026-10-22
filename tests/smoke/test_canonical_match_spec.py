"""Legacy MatchSpec adapter parity for the canonical compiler seam."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.services.position_match.canonical import (
    canonical_match_spec_to_json,
    canonicalize_legacy_match_spec,
    finalize_canonical_match_spec,
)
from app.services.position_match.compiler import compile_parsed_query
from app.services.position_match.spec import MatchSpec, SlotConstraint
from app.services.query_parse import normalize_and_parse


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "contracts" / "match-spec-cases.json"


class CanonicalMatchSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(CASES.read_text(encoding="utf-8"))

    def test_legacy_adapter_matches_shared_corpus(self) -> None:
        for item in self.doc["cases"]:
            with self.subTest(item["id"]):
                parsed = normalize_and_parse(item["query"], mode=item["mode"])
                got = canonical_match_spec_to_json(compile_parsed_query(parsed))
                self.assertEqual(got, item["expected"])

    def test_lookup_is_not_in_match_spec_corpus(self) -> None:
        queries = {item["query"] for item in self.doc["cases"]}
        self.assertNotIn("香港", queries)
        self.assertNotIn("事業", queries)

    def test_non_match_query_is_rejected_at_compiler_seam(self) -> None:
        with self.assertRaises(ValueError):
            compile_parsed_query(normalize_and_parse("香港"))

    def test_rhyme_with_code_search_ignores_anchor_tone(self) -> None:
        from app.domain.lexicon.phoneme_codec import encode_phoneme_list
        from app.models.word import Word
        from app.services.query_dispatch import search_words
        from tests.smoke.helpers import memory_sessionmaker

        Session = memory_sessionmaker()
        with Session() as db:
            for char, jyutping, code, initials, finals in [
                ("墨", "mak6", "2", ["m"], ["ak"]),
                ("黑客", "hak1 haak3", "34", ["h", "h"], ["ak", "aak"]),
                ("麥片", "mak6 pin3", "24", ["m", "p"], ["ak", "in"]),
                ("黑雨", "hak1 jyu5", "35", ["h", "j"], ["ak", "yu"]),
                ("麥粉", "mak6 fan2", "29", ["m", "f"], ["ak", "an"]),
                ("拍攝", "paak3 sip3", "44", ["p", "s"], ["aak", "ip"]),
            ]:
                db.add(Word(
                    char=char, jyutping=jyutping, code=code, length=len(char),
                    initials=encode_phoneme_list(initials, "initial"),
                    finals=encode_phoneme_list(finals, "final"),
                ))
            db.commit()
            for mode in ("m1", "m2", "m3"):
                with self.subTest(mode=mode):
                    rows = search_words(q="墨=4", mode=mode, db=db, limit=100, offset=0)
                    expected = {"黑客", "麥片"} | ({"黑雨"} if mode != "m3" else set())
                    self.assertEqual({row["char"] for row in rows}, expected)

    def test_legacy_adapter_returns_a_canonical_value(self) -> None:
        canonical = canonicalize_legacy_match_spec(
            MatchSpec(
                width=2,
                slots=[SlotConstraint(pos=1, kind="literal_char", value="港")],
                mask="?港",
            )
        )
        self.assertEqual(canonical.width, 2)
        self.assertEqual(canonical.mask, "?港")

    def test_finalizer_rejects_conflicting_same_kind_constraints(self) -> None:
        with self.assertRaisesRegex(ValueError, "conflicting slot"):
            finalize_canonical_match_spec(
                width=1,
                slots=[
                    SlotConstraint(pos=0, kind="code_digit", value="2"),
                    SlotConstraint(pos=0, kind="code_digit", value="3"),
                ],
            )

    def test_finalizer_projects_mask_from_owning_slots(self) -> None:
        canonical = finalize_canonical_match_spec(
            width=2,
            slots=[SlotConstraint(pos=1, kind="code_digit", value="0")],
            mask="門0",
        )
        self.assertEqual(canonical.mask, "門0")
        self.assertIn(
            ("literal_char", "門", "門"),
            [(slot.kind, slot.value, slot.mask_token) for slot in canonical.slots],
        )

    def test_finalizer_rejects_unowned_mask_digit(self) -> None:
        with self.assertRaisesRegex(ValueError, "no owning slot"):
            finalize_canonical_match_spec(
                width=1,
                slots=[SlotConstraint(pos=0, kind="code_digit", value="2")],
                mask="3",
            )


if __name__ == "__main__":
    unittest.main()
