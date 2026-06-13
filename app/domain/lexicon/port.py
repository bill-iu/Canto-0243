"""Raw 詞庫埠 — rime 單字與詞級標音 lookup，不帶收錄決策。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Protocol, runtime_checkable

from app.lexicon.static_index import LexiconEntry


@runtime_checkable
class LexiconPort(Protocol):
    def ensure_loaded(self) -> None:
        ...

    def get_rime_char_entries(self, char: str) -> List[LexiconEntry]:
        ...

    def get_word_lexicon_entries(self, text: str) -> List[LexiconEntry]:
        ...


class Static0243Lexicon:
    """詞級標音 JSON（maintainer import；runtime 預設讀本地 gitignore 目錄）。"""

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

    def get_rime_char_entries(self, char: str) -> List[LexiconEntry]:
        return []

    def get_word_lexicon_entries(self, text: str) -> List[LexiconEntry]:
        from app.lexicon.static_index import get_lexicon_entries

        self.ensure_loaded()
        return get_lexicon_entries(text)


class CompositeLexicon:
    """單字 rime char.csv；多字詞級標音 JSON。"""

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

    def get_rime_char_entries(self, char: str) -> List[LexiconEntry]:
        from app.lexicon.rime_char_index import get_rime_char_entries

        self.ensure_loaded()
        return get_rime_char_entries(char)

    def get_word_lexicon_entries(self, text: str) -> List[LexiconEntry]:
        from app.lexicon.static_index import get_lexicon_entries

        self.ensure_loaded()
        return get_lexicon_entries(text)


_default_port = CompositeLexicon(auto_load=False)


def default_lexicon_port() -> LexiconPort:
    return _default_port


__all__ = [
    "CompositeLexicon",
    "LexiconPort",
    "Static0243Lexicon",
    "default_lexicon_port",
]
