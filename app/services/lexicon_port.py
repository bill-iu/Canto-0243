"""Mockable port for lexicon lookup (收錄門檻 + 讀音權威)."""

from __future__ import annotations

from typing import List, Protocol, runtime_checkable

from app.lexicon.static_index import LexiconEntry


@runtime_checkable
class LexiconPort(Protocol):
    def ensure_loaded(self) -> None:
        ...

    def get_entries(self, char: str) -> List[LexiconEntry]:
        ...


class Static0243Lexicon:
    """Default runtime implementation backed by bundled ingest JSON."""

    def __init__(self, *, auto_load: bool = True, clean_dir: str | None = None) -> None:
        self._clean_dir = clean_dir
        self._loaded = False
        if auto_load:
            self.ensure_loaded()

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        from app.lexicon.static_index import ensure_lexicon_loaded

        ensure_lexicon_loaded(self._clean_dir)
        self._loaded = True

    def get_entries(self, char: str) -> List[LexiconEntry]:
        from app.lexicon.static_index import get_lexicon_entries

        self.ensure_loaded()
        return get_lexicon_entries(char)


_default_port = Static0243Lexicon(auto_load=False)


def default_lexicon_port() -> LexiconPort:
    return _default_port
