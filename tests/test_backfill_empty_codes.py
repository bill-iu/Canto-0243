import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from scripts.backfill_empty_codes import backfill_empty_codes


class BackfillEmptyCodesTests(unittest.TestCase):
    def test_backfill_and_dedupe(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all([
                Word(id=1, char="主僕", code="92", jyutping="zyu2 buk6", length=2),
                Word(id=2, char="主僕", code="", jyutping="zyu2 buk6", length=2),
                Word(id=3, char="生死", code="", jyutping="saang1 sei2", length=2),
            ])
            db.commit()

            stats = backfill_empty_codes(db, dry_run=False, batch_size=50)
            self.assertEqual(stats["updated_code"], 1)
            self.assertEqual(stats["deleted_duplicate"], 1)

            rows = {w.id: w for w in db.query(Word).order_by(Word.id).all()}
            self.assertNotIn(2, rows)
            self.assertEqual(rows[1].code, "92")
            self.assertEqual(rows[3].code, "39")


if __name__ == "__main__":
    unittest.main()
