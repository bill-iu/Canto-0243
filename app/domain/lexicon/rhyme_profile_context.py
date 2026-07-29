"""Request-scoped 韻母比對檔 for Portable filters."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

from app.domain.lexicon.rhyme_match_profile import normalize_rhyme_profile

_rhyme_profile: ContextVar[str] = ContextVar("rhyme_profile", default="exact")


def get_rhyme_profile() -> str:
    return _rhyme_profile.get()


def set_rhyme_profile(profile: object) -> None:
    _rhyme_profile.set(normalize_rhyme_profile(profile))


@contextmanager
def rhyme_profile_scope(profile: object) -> Iterator[None]:
    token = _rhyme_profile.set(normalize_rhyme_profile(profile))
    try:
        yield
    finally:
        _rhyme_profile.reset(token)
