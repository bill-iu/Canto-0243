from app.database import SessionLocal
from app.services.query_dispatch import search_words
db = SessionLocal()
for q in ["?困潦倒=", "香港=", "就=", "3$漢4"]:
    items = search_words(q=q, mode="m1", limit=5, offset=0, db=db)
    sample = []
    for i in items[:3]:
        sample.append(i.get("char") if isinstance(i, dict) else getattr(i, "char", str(i)))
    print(repr(q), "n=", len(items), sample)
db.close()
