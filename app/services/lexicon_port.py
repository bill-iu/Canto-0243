"""Mockable port for lexicon lookup (收錄門檻 + 讀音權威)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Protocol, runtime_checkable

from app.lexicon.static_index import LexiconEntry


@runtime_checkable
class LexiconPort(Protocol):
    def ensure_loaded(self) -> None:
        ...

    def get_entries(self, char: str) -> List[LexiconEntry]:
        ...


class Static0243Lexicon:
    """Word-level entries from bundled ingest JSON (data/raw/clean)."""

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


class CompositeLexicon:
    """Single-char from rime char.csv; multi-char from static 0243 JSON."""

    def __init__(
        self,
        *,
        auto_load: bool = True,
        clean_dir: str | None = None,
        rime_char_csv: str | Path | None = None,
    ) -> None:
        self._clean_dir = clean_dir
        self._rime_char_csv = rime_char_csv
        self._loaded = False
        if auto_load:
            self.ensure_loaded()

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        from app.lexicon.rime_char_index import ensure_rime_char_loaded
        from app.lexicon.static_index import ensure_lexicon_loaded

        ensure_lexicon_loaded(self._clean_dir)
        ensure_rime_char_loaded(self._rime_char_csv)
        self._loaded = True

    def get_entries(self, char: str) -> List[LexiconEntry]:
        from app.lexicon.rime_char_index import get_rime_char_entries
        from app.lexicon.static_index import get_lexicon_entries

        self.ensure_loaded()
        text = (char or "").strip()
        if not text:
            return []
        if len(text) == 1:
            return get_rime_char_entries(text)
        static_entries = get_lexicon_entries(text)
        if static_entries:
            return static_entries
        from app.utils.syllable_reading import compose_lexicon_entries_from_rime

        return compose_lexicon_entries_from_rime(text)


_default_port = CompositeLexicon(auto_load=False)


def default_lexicon_port() -> LexiconPort:
    return _default_port
