"""Candidate sources and mask-family source registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.domain.lexicon.ranking import literal_priority_sort_key
from app.models.word import Word
from app.services.position_match.spec import CandidateSource, MatchSpec, SlotConstraint
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_query_parser import matches_mask_literal_chars
from app.services.word_serializer import get_word_jyutping, get_word_sort_code, get_word_text
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import (
    get_mask_index_candidates,
    get_phoneme_index_candidates,
    get_words_for_length,
    is_word_cache_ready,
)


@dataclass
class LengthMaskCandidateSource:
    """Cache-first 長度桶 + mask literal 預過濾（碼字 tail／字面參考）。"""

    db: Any
    mask: str

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        return get_length_candidates(self.db, length, self.mask)


@dataclass
class RhymeAnchorCandidateSource:
    """韻／聲錨：cache-ready 時直接走音素倒排索引，跳過全桶掃描。"""

    db: Any
    mask: str
    anchor_pos: int
    anchor: str
    constraint: str

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        return get_rhyme_anchor_length_candidates(
            self.db,
            length,
            self.mask,
            self.anchor_pos,
            self.anchor,
            self.constraint,
        )


@dataclass
class LengthCodeCandidateSource:
    """Cache-first 長度桶 + 可選 0243 碼過濾（hybrid 等）。"""

    db: Any
    code: Optional[str] = None
    mode: str = "m1"
    fallback_limit: int = 2000

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        effective_code = code if code is not None else self.code
        effective_mode = mode or self.mode
        return get_candidates_for_length(
            self.db,
            length,
            code=effective_code,
            mode=effective_mode,
            fallback_limit=self.fallback_limit,
        )


@dataclass
class MaskWildcardCandidateSource:
    """缺字查詢：cache literal 預過濾或 DB GLOB + 可選 code filter。"""

    db: Any
    mask: str
    mode: str = "m1"
    query_code: Optional[str] = None

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        from app.services.word_query_parser import mask_char_glob_pattern, mask_fixed_literal_prefix, parse_mask_query

        effective_mode = mode or self.mode
        effective_code = code if code is not None else self.query_code
        _, required_codes, _ = parse_mask_query(self.mask)

        indexed = get_mask_index_candidates(length, self.mask)
        if indexed is not None:
            candidates = indexed
        else:
            candidates = get_words_for_length(length)
        if candidates:
            return [
                w for w in candidates
                if matches_mask_literal_chars(get_word_text(w), self.mask)
            ], True

        glob_pat = mask_char_glob_pattern(self.mask)
        query = self.db.query(Word).filter(
            length_filter(length),
            Word.char.op("GLOB")(glob_pat),
        )
        prefix = mask_fixed_literal_prefix(self.mask)
        if prefix:
            query = query.filter(Word.char.like(f"{prefix}%"))
        code_filter = "".join(required_codes) if all(req is not None for req in required_codes) else None
        if code_filter:
            query = apply_code_filter(query, code_filter, effective_mode)
        elif effective_code:
            query = apply_code_filter(query, effective_code, effective_mode)
        return query.order_by(Word.char, Word.jyutping).all(), False


def get_length_candidates(db, width: int, mask: str):
    """
    取得指定長度的候選詞，並對 cache 命中者先做 mask literal 預過濾。
    用於 rhyme-anchor、code-tail、at-tail 等需要 mask 的情境。
    """
    indexed = get_mask_index_candidates(width, mask)
    if indexed is not None:
        candidates = indexed
    else:
        candidates = get_words_for_length(width)
    if candidates:
        return [w for w in candidates if matches_mask_literal_chars(get_word_text(w), mask)], True
    from app.services.word_query_parser import mask_char_glob_pattern as _mask_glob
    from app.services.word_query_parser import mask_fixed_literal_prefix

    glob_pat = _mask_glob(mask)
    query = db.query(Word).filter(
        length_filter(width),
        Word.char.op("GLOB")(glob_pat),
    )
    prefix = mask_fixed_literal_prefix(mask)
    if prefix:
        query = query.filter(Word.char.like(f"{prefix}%"))
    return query.order_by(Word.char, Word.jyutping).all(), False


def get_rhyme_anchor_length_candidates(
    db,
    width: int,
    mask: str,
    anchor_pos: int,
    anchor: str,
    constraint: str,
) -> tuple[list[Any], bool]:
    """韻／聲錨候選：音素索引優先，避免先物化整個 length 桶。"""
    if is_word_cache_ready():
        rows = get_phoneme_index_candidates(width, anchor_pos, anchor, constraint, db)
        narrowed = [
            w for w in rows
            if matches_mask_literal_chars(get_word_text(w), mask)
        ]
        return narrowed, True
    return get_length_candidates(db, width, mask)


def get_candidates_for_length(
    db: Any,
    length: int,
    *,
    code: Optional[str] = None,
    mode: str = "m1",
    fallback_limit: int = 2000,
):
    """
    通用長度候選取得（無 mask 預過濾）。
    用於 hybrid 等情境。
    """
    candidates = get_words_for_length(length)
    if candidates:
        return candidates, True
    query = db.query(Word).filter(length_filter(length))
    if code:
        query = apply_code_filter(query, code, mode)
    return query.order_by(Word.char, Word.jyutping).limit(fallback_limit).all(), False


def _phoneme_anchor_slot(spec: MatchSpec) -> Optional[SlotConstraint]:
    for slot in spec.slots:
        if slot.kind in ("final_anchor", "initial_anchor"):
            return slot
    return None


def _resolve_mask_family_source(
    spec: MatchSpec,
    db: Any,
    mode: str,
    query_code: Optional[str],
) -> tuple[Optional[CandidateSource], Optional[Callable]]:
    """由 MatchSpec 形狀選擇候選來源（registry，不依 ParsedQuery）。"""
    if spec.literal_priority and spec.mask:
        effective_code = query_code or spec.code_prefix
        source = MaskWildcardCandidateSource(
            db, spec.mask, mode=mode, query_code=effective_code
        )
        literal_positions = spec.extra.get("literal_positions", [])
        sort_key = lambda w: literal_priority_sort_key(w, literal_positions)
        return source, sort_key

    if spec.hybrid_ref_chars:
        source = LengthCodeCandidateSource(db, code=spec.code_prefix, mode=mode)
        return source, None

    anchor = _phoneme_anchor_slot(spec)
    if anchor and spec.mask and not spec.literal_priority:
        constraint = "final" if anchor.kind == "final_anchor" else "initial"
        source = RhymeAnchorCandidateSource(
            db,
            spec.mask,
            anchor.pos,
            anchor.value or "",
            constraint,
        )
        return source, None

    if spec.mask:
        return LengthMaskCandidateSource(db, spec.mask), None

    return None, None