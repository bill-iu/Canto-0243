"""靜態詞林埠 — CONTEXT § 靜態詞林埠（raw lookup，不帶收錄判斷）。"""

from __future__ import annotations

from typing import Iterator, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class ThesaurusPort(Protocol):
    def ensure_loaded(self) -> None:
        ...

    def get_cilin_synonyms(self, word: str) -> List[str]:
        ...

    def get_guotong_synonyms(self, word: str) -> List[str]:
        ...

    def get_synonyms(self, query: str) -> List[str]:
        ...

    def get_antonyms(self, query: str) -> List[str]:
        ...

    def iter_antonym_edges(self) -> Iterator[Tuple[str, str]]:
        ...

    def iter_literal_heads(self) -> Iterator[str]:
        ...


class StaticThesaurusPort:
    """File-backed 靜態詞林；可指定路徑（ingest manifest）或使用 repo 預設。"""

    def __init__(
        self,
        *,
        cilin_path: str | None = None,
        antisem_path: str | None = None,
        thesaurus_syn_path: str | None = None,
        thesaurus_ant_path: str | None = None,
        auto_load: bool = True,
    ) -> None:
        self._cilin_path = cilin_path
        self._antisem_path = antisem_path
        self._thesaurus_syn_path = thesaurus_syn_path
        self._thesaurus_ant_path = thesaurus_ant_path
        self._loaded = False
        self._use_defaults = not any(
            [cilin_path, antisem_path, thesaurus_syn_path, thesaurus_ant_path]
        )
        if auto_load:
            self.ensure_loaded()

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        if self._use_defaults:
            from app.thesaurus.static_index import ensure_thesaurus_loaded

            ensure_thesaurus_loaded()
        else:
            from app.thesaurus.static_index import (
                load_antonym_dict,
                load_cilin_index,
                load_thesaurus_dicts,
            )

            if self._cilin_path:
                load_cilin_index(self._cilin_path)
            if self._antisem_path:
                load_antonym_dict(self._antisem_path)
            if self._thesaurus_syn_path or self._thesaurus_ant_path:
                load_thesaurus_dicts(
                    self._thesaurus_syn_path or "data/thesaurus/dict_synonym.txt",
                    self._thesaurus_ant_path or "data/thesaurus/dict_antonym.txt",
                )
        self._loaded = True

    def get_cilin_synonyms(self, word: str) -> List[str]:
        from app.thesaurus.static_index import get_cilin_synonyms

        self.ensure_loaded()
        return get_cilin_synonyms(word)

    def get_guotong_synonyms(self, word: str) -> List[str]:
        from app.thesaurus.static_index import get_guotong_synonyms

        self.ensure_loaded()
        return get_guotong_synonyms(word)

    def get_synonyms(self, query: str) -> List[str]:
        from app.thesaurus.static_index import get_synonyms

        try:
            self.ensure_loaded()
            return get_synonyms(query)
        except Exception:
            return []

    def get_antonyms(self, query: str) -> List[str]:
        from app.thesaurus.static_index import get_antonyms

        try:
            self.ensure_loaded()
            return get_antonyms(query)
        except Exception:
            return []

    def iter_antonym_edges(self) -> Iterator[Tuple[str, str]]:
        from app.thesaurus.static_index import iter_antonym_edges

        self.ensure_loaded()
        return iter_antonym_edges()

    def iter_literal_heads(self) -> Iterator[str]:
        from app.thesaurus.static_index import iter_literal_heads

        self.ensure_loaded()
        return iter_literal_heads()


_default_port = StaticThesaurusPort(auto_load=False)


def default_thesaurus_port() -> ThesaurusPort:
    return _default_port


__all__ = [
    "StaticThesaurusPort",
    "ThesaurusPort",
    "default_thesaurus_port",
]
