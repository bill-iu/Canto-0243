"""Maintainer compatibility exports; the phoneme contract ships in Desktop."""
from app.domain.lexicon.phoneme_meta import (
    KEY_PHONEME_VOCAB_FP,
    KEY_PHONEME_VOCAB_VERSION,
    ensure_lexicon_meta_table,
    ensure_phoneme_storage_contract,
    phoneme_storage_contract_ok,
    phoneme_vocab_meta_ok,
    read_phoneme_vocab_meta,
    samples_legacy_json_phoneme,
    write_phoneme_vocab_meta,
)
