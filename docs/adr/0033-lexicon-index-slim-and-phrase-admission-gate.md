# Lexicon index slim and phrase admission gate (v1.0.7 I2)

PWA and Portable ship a single SQLite `lyrics.db`. After ADR-0027 schema slimming, the artifact still grew to ~189 MB because secondary indexes dominated (~60% of file bytes) and `rime_phrase` ingest contributed ~300k low-value rows (shop/place names).

We will not split the lexicon into multiple files for v1.0.7 (S0). Instead:

1. **Index allowlist** — After `build-db`, `finalize_lexicon_indexes` drops duplicate and unused indexes (Tier1–3 audit). SQLAlchemy model stops creating redundant single-column indexes; `bootstrap.py` no longer recreates legacy `idx_length_code` / duplicate length indexes. Retained: `ix_words_char`, `idx_length_code_finals`, relation composites, `uq_word_relation`.

2. **Phrase admission gate** — Expand **短語收錄門檻** with maintainer file `jyut6ping3.phrase.reject-suffixes.txt` (B + limited built-in org suffixes). Reject ≥4-char literals ending in `路`; do not single-char-suffix `路` (keeps 套路/出路).

3. **Release gate** — `check_lexicon_release_gate`: db ≤95 MB, indexes ≤45 MB, rime_phrase rows ↓≥50% vs baseline, golden parity and G benchmark enforced separately.

**I3 (phoneme compact encoding, J2)** — see **[ADR-0037](./0037-phoneme-field-compact-encoding.md)** (S1 compact fields + vocab meta; after I2 dual-channel stability).

**Consequences**

- `python -m ingest build-db` fails if release gate fails after finalize.
- Portable and PWA continue single-file delivery.
- Rebuild required; hotfix purge of `words` rows is not the SSOT path.