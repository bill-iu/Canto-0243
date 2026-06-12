"""Deprecated project-root facade for ingest scripts and legacy callers.

Application code under ``app/`` should import from ``app.utils.*`` or
``app.thesaurus.*`` directly. This module remains for ``ingest/``,
``scripts/legacy/generate_relationships.py``, and similar offline tooling.
"""

from app.thesaurus import static_index as _thesaurus
from app.utils import embedding as _embedding
from app.utils import jyutping_codec as _codec
from app.utils import json_helpers as _json
from app.utils import word_cache as _cache

# --- 0243 / jyutping ---
TONE_MAP = _codec.TONE_MAP
VOWELS = _codec.VOWELS
M1_MAPPING = _codec.M1_MAPPING
get_0243_code = _codec.get_0243_code
split_jyutping = _codec.split_jyutping
get_code_variants = _codec.get_code_variants

# --- JSON helpers ---
load_json_list = _json.load_json_list

# --- Embedding (ingest-only) ---
get_text_embedding = _embedding.get_text_embedding
is_embedding_model_ready = _embedding.is_embedding_model_ready
enable_embedding_model_for_ingest = _embedding.enable_embedding_model_for_ingest
cosine_similarity = _embedding.cosine_similarity

# --- Legacy synonym matrix ---
set_synonym_index = _thesaurus.set_synonym_index
get_synonym_index = _thesaurus.get_synonym_index

# --- Static thesaurus dict aliases (updated after loaders) ---
_cilin_syns: dict = {}
_syn_dict: dict = {}
_ant_dict: dict = {}


def _refresh_thesaurus_aliases() -> None:
    global _cilin_syns, _syn_dict, _ant_dict
    _cilin_syns, _syn_dict, _ant_dict = _thesaurus.get_internal_dicts()


_refresh_thesaurus_aliases()


def load_cilin_index(path: str = "data/cilin/new_cilin.txt") -> None:
    _thesaurus.load_cilin_index(path)
    _refresh_thesaurus_aliases()


def get_cilin_synonyms(word: str):
    return _thesaurus.get_cilin_synonyms(word)


def load_antonym_dict(path: str = "data/antonym/antisem.txt") -> None:
    _thesaurus.load_antonym_dict(path)
    _refresh_thesaurus_aliases()


def load_thesaurus_dicts(
    syn_path: str = "data/thesaurus/dict_synonym.txt",
    ant_path: str = "data/thesaurus/dict_antonym.txt",
) -> None:
    _thesaurus.load_thesaurus_dicts(syn_path, ant_path)
    _refresh_thesaurus_aliases()


def get_synonyms(q: str):
    return _thesaurus.get_synonyms(q)


def get_antonyms(q: str):
    return _thesaurus.get_antonyms(q)


def ensure_thesaurus_loaded(force: bool = False) -> None:
    _thesaurus.ensure_thesaurus_loaded(force)
    _refresh_thesaurus_aliases()


# --- Word cache ---
populate_word_cache_from_rows = _cache.populate_word_cache_from_rows
get_words_for_length = _cache.get_words_for_length
get_char_meta = _cache.get_char_meta
get_char_metas = _cache.get_char_metas
update_word_in_cache = _cache.update_word_in_cache
get_word_cache_stats = _cache.get_word_cache_stats
