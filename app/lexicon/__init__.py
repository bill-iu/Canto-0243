"""Bundled 0243 lexicon index (ingest JSON mirror for runtime ensure)."""

from app.lexicon.static_index import ensure_lexicon_loaded, get_lexicon_entries
from app.lexicon.rime_char_index import ensure_rime_char_loaded, get_rime_char_entries
from app.lexicon.essay_index import ensure_essay_loaded, get_essay_frequency

__all__ = [
    "ensure_lexicon_loaded",
    "get_lexicon_entries",
    "ensure_rime_char_loaded",
    "get_rime_char_entries",
    "ensure_essay_loaded",
    "get_essay_frequency",
]
