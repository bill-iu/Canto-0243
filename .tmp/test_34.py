import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["READINESS_GATE_ENFORCE"] = "0"

from app.lexicon.rime_char_index import reset_rime_char_for_tests
from app.models.word import Word
from app.services.query_dispatch import search_words
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base

reset_rime_char_for_tests()  # simulate CI: no char.csv

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
with Session() as db:
    db.add_all([
        Word(char="好我", code="34", jyutping="hou2 ngo5", finals='["ou", "o"]', initials='["h", "ng"]', length=2),
        Word(char="小馬騮", code="944", jyutping="siu2 maa5 ngau4", finals='["iu", "aa", "au"]', initials='["s", "m", "ng"]', length=3),
    ])
    db.commit()
    results = search_words(q="34=我", mode="m1", db=db, limit=10, offset=0)
    words = [r["char"] for r in results if r.get("result_type") == "word"]
    print("no rime:", words)