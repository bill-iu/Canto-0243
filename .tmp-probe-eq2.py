import os
import sqlite3

os.environ["READINESS_GATE_ENFORCE"] = "0"

c = sqlite3.connect("lyrics.db")
for lit in ["香港", "窮困潦倒", "困潦倒", "門", "就"]:
    rows = c.execute(
        "SELECT char, code, jyutping, finals, initials FROM words WHERE char=? LIMIT 3",
        (lit,),
    ).fetchall()
    print(repr(lit), "n=", len(rows), rows[:2])
c.close()

from app.startup.readiness_gate import reset_readiness_gate_for_tests

reset_readiness_gate_for_tests()
from app.database import SessionLocal
from app.services.query_dispatch import QueryEngine, SearchContext

db = SessionLocal()
eng = QueryEngine()
for q in ["?困潦倒=", "+門=0", "0449窮困潦倒=", "04困=49倒=", "香港="]:
    r = eng.execute(
        SearchContext(q=q, mode="m1", limit=3, offset=0, db=db, code=None, char=None)
    )
    chars = [
        (x.get("char") if isinstance(x, dict) else getattr(x, "char", None))
        for x in r.items[:3]
    ]
    print("Q", q, "n=", len(r.items), chars)
db.close()
