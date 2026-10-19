"""A sealed Desktop lexicon must open without the maintainer-only ingest package."""
import builtins
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.db.bootstrap import ensure_phoneme_compact_contract
from app.domain.lexicon.phoneme_codec import encode_phoneme_list
from app.domain.lexicon.phoneme_meta import write_phoneme_vocab_meta


class DesktopPhonemeBootstrapTests(unittest.TestCase):
    def test_sealed_database_opens_without_ingest(self):
        original_import = builtins.__import__

        def runtime_import(name, *args, **kwargs):
            if name == 'ingest' or name.startswith('ingest.'):
                raise ModuleNotFoundError('ingest is not shipped in Desktop')
            return original_import(name, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path = root / 'lyrics.db'
            with closing(sqlite3.connect(db_path)) as db:
                db.execute('CREATE TABLE words (initials TEXT, finals TEXT)')
                db.execute('INSERT INTO words VALUES (?, ?)', (
                    encode_phoneme_list(['h', 'g'], 'initial'),
                    encode_phoneme_list(['oeng', 'ong'], 'final'),
                ))
                db.commit()
            write_phoneme_vocab_meta(db_path)
            with patch('app.db.connection.PROJECT_ROOT', root), patch(
                'builtins.__import__', side_effect=runtime_import
            ):
                ensure_phoneme_compact_contract()
