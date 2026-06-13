import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from scripts.export_words_lexicon import export_words_lexicon


class ExportWordsLexiconTests(unittest.TestCase):
    def test_export_writes_char_jyutping_code_rows(self):
        from app.database import Base
        from app.models.word import Word

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            engine = create_engine(f"sqlite:///{db_path}")
            Base.metadata.create_all(bind=engine)
            Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            with Session() as db:
                db.add(
                    Word(
                        char="你好",
                        code="45",
                        jyutping="nei5 hou2",
                        length=2,
                    )
                )
                db.commit()
            engine.dispose()

            rows = export_words_lexicon(db_path)

        self.assertEqual(
            rows,
            [{"char": "你好", "code": "45", "jyutping": "nei5 hou2"}],
        )


if __name__ == "__main__":
    unittest.main()
