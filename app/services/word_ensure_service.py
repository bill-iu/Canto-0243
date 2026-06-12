from __future__ import annotations

import re
from typing import List

from sqlalchemy.orm import Session

from app.models.word import Word
from app.utils.jyutping_codec import get_0243_code, split_jyutping
from app.utils.word_cache import update_word_in_cache


def sync_word_to_cache(row) -> None:
    try:
        update_word_in_cache(
            row.char,
            getattr(row, "code", "") or "",
            getattr(row, "jyutping", "") or "",
            getattr(row, "finals", None),
            getattr(row, "initials", None),
            getattr(row, "length", None),
        )
    except Exception:
        pass


def ensure_word_in_db(db: Session, text: str) -> List[Word]:
    if not text or not text.strip():
        return []
    text = text.strip()
    existing = db.query(Word).filter(Word.char == text).all()
    if existing:
        return existing
    if not re.search(r"[\u4e00-\u9fff]", text):
        return []
    jyut_str = ""
    try:
        import pycantonese
        jyut_list = pycantonese.characters_to_jyutping(text)
        if jyut_list:
            jyut_str = " ".join([item[1] for item in jyut_list if item and len(item) > 1 and item[1]])
    except Exception as e:
        print(f"[ensure] pycantonese error for {text}: {e}")
    if not jyut_str:
        try:
            from pyjyutping import jyutping as pyjy
            cand = pyjy.convert(text)
            if cand:
                jyut_str = cand
        except Exception:
            pass
    if not jyut_str:
        return []
    code_val = get_0243_code(jyut_str) or ""
    try:
        initials, finals, tones = split_jyutping(jyut_str)
    except Exception:
        initials = finals = tones = "[]"
    db_word = Word(
        char=text,
        code=code_val,
        jyutping=jyut_str,
        initials=initials,
        finals=finals,
        tones=tones,
        length=len(text),
        meaning=None,
    )
    db.add(db_word)
    try:
        db.commit()
        db.refresh(db_word)
        print(f"[ensure] injected into DB: '{text}' (code={code_val}, jyut={jyut_str})")
        sync_word_to_cache(db_word)
        return [db_word]
    except Exception as e:
        db.rollback()
        print(f"[ensure] DB insert failed for {text}: {type(e).__name__}: {e}")
        return []
