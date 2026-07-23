from __future__ import annotations

import unittest

from sqlalchemy import event

from app.models.word import Word
from app.services.workbench.line_readings import resolve_line_readings
from tests.smoke.helpers import memory_sessionmaker


class WorkbenchLineReadingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.Session = memory_sessionmaker()

    def test_single_reading_and_multi_character_sentence(self) -> None:
        with self.Session() as db:
            db.add_all([
                Word(char="香", code="3", jyutping="hoeng1", initials='["h"]', finals='["oeng"]', length=1),
                Word(char="港", code="9", jyutping="gong2", initials='["g"]', finals='["ong"]', length=1),
            ])
            db.commit()
            slots = resolve_line_readings("香港", db)

        self.assertEqual([slot.surface for slot in slots], ["香", "港"])
        self.assertEqual(slots[0].choices[0].jyutping, "hoeng1")
        self.assertFalse(slots[0].needs_choice)

    def test_materially_different_same_code_readings_need_choice(self) -> None:
        with self.Session() as db:
            db.add_all([
                Word(char="你", code="5", jyutping="nei5", initials='["n"]', finals='["ei"]', length=1),
                Word(char="你", code="5", jyutping="lei5", initials='["l"]', finals='["ei"]', length=1),
            ])
            db.commit()
            slot = resolve_line_readings("你", db)[0]

        self.assertTrue(slot.needs_choice)
        self.assertEqual({choice.initial for choice in slot.choices}, {"n", "l"})

    def test_duplicate_rows_collapse_and_authoritative_reading_is_first(self) -> None:
        with self.Session() as db:
            db.add_all([
                Word(char="難", code="0", jyutping="no4", initials='["n"]', finals='["o"]', length=1),
                Word(char="難", code="0", jyutping="naan4", initials='["n"]', finals='["aan"]', length=1),
                Word(char="難", code="0", jyutping="naan4", initials='["n"]', finals='["aan"]', length=1),
            ])
            db.commit()
            slot = resolve_line_readings("難", db)[0]

        self.assertEqual(slot.choices[0].jyutping, "naan4")
        self.assertEqual(sum(choice.jyutping == "naan4" for choice in slot.choices), 1)

    def test_missing_character_and_punctuation_stay_editable(self) -> None:
        with self.Session() as db:
            slots = resolve_line_readings("𠮶，", db)

        self.assertEqual(slots[0].kind, "unresolved")
        self.assertEqual(slots[0].choices, ())
        self.assertEqual(slots[1].kind, "punctuation")
        self.assertFalse(slots[1].needs_choice)

    def test_duplicate_literals_use_one_read_only_batch_query(self) -> None:
        with self.Session() as db:
            db.add_all([
                Word(char="香", code="3", jyutping="hoeng1", initials='["h"]', finals='["oeng"]', length=1),
                Word(char="港", code="9", jyutping="gong2", initials='["g"]', finals='["ong"]', length=1),
            ])
            db.commit()
            statements: list[str] = []

            def record(_conn, _cursor, statement, _params, _context, _many) -> None:
                if statement.lstrip().upper().startswith(("SELECT", "INSERT", "UPDATE", "DELETE")):
                    statements.append(statement)

            bind = db.get_bind()
            event.listen(bind, "before_cursor_execute", record)
            try:
                slots = resolve_line_readings("香香港，", db)
            finally:
                event.remove(bind, "before_cursor_execute", record)
            row_count = db.query(Word).count()

        self.assertEqual([slot.surface for slot in slots], ["香", "香", "港", "，"])
        self.assertEqual(len(statements), 1, statements)
        self.assertIn("SELECT", statements[0].upper())
        self.assertNotIn("INSERT", statements[0].upper())
        self.assertEqual(row_count, 2)


if __name__ == "__main__":
    unittest.main()
