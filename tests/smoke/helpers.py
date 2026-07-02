"""Shared helpers for smoke tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DB = REPO_ROOT / "tests" / "fixtures" / "lyrics.db"
CILIN_SAMPLE = REPO_ROOT / "data" / "syn_ant" / "fixtures" / "cilin_sample.txt"


def skip_without_fixture_db() -> None:
    if not FIXTURE_DB.is_file():
        raise unittest.SkipTest(f"missing {FIXTURE_DB}")


def fixture_sessionmaker():
    skip_without_fixture_db()
    engine = create_engine(f"sqlite:///{FIXTURE_DB.as_posix()}")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def memory_sessionmaker():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def seed_happy_sad(db) -> None:
    db.add_all([
        Word(id=1, char="快樂", code="22", jyutping="", length=2),
        Word(id=2, char="開心", code="22", jyutping="", length=2),
        Word(id=3, char="愉快", code="22", jyutping="", length=2),
        Word(id=4, char="悲傷", code="22", jyutping="", length=2),
        Word(id=5, char="傷心", code="22", jyutping="", length=2),
    ])
    db.add_all([
        WordRelation(word_id=1, related_id=2, relation_type="syn", score=0.95, source="cilin"),
        WordRelation(word_id=1, related_id=3, relation_type="syn", score=0.80, source="test"),
        WordRelation(word_id=2, related_id=4, relation_type="ant", score=0.90, source="guotong"),
        WordRelation(word_id=2, related_id=5, relation_type="ant", score=0.70, source="ant_syn_bridge"),
    ])
    db.commit()
