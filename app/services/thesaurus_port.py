"""Mockable port for static thesaurus (cilin / antisem / dict files)."""

from __future__ import annotations

from typing import Iterator, List, Protocol, Tuple, runtime_checkable


@runtime_checkable
class ThesaurusPort(Protocol):
    def ensure_loaded(self) -> None:
        ...

    def get_synonyms(self, query: str) -> List[str]:
        ...

    def get_antonyms(self, query: str) -> List[str]:
        ...

    def iter_antonym_edges(self) -> Iterator[Tuple[str, str]]:
        ...


class StaticThesaurusPort:
    """Default runtime implementation backed by ``app.thesaurus.static_index``."""

    def __init__(self, *, auto_load: bool = True) -> None:
        self._loaded = False
        if auto_load:
            self.ensure_loaded()

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        from app.thesaurus.static_index import ensure_thesaurus_loaded

        ensure_thesaurus_loaded()
        self._loaded = True

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


_default_port = StaticThesaurusPort(auto_load=False)


def default_thesaurus_port() -> ThesaurusPort:
    return _default_port
