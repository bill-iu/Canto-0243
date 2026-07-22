"""Candidate sources and mask-family source registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.domain.lexicon.ranking import literal_priority_sort_key
from app.models.word import Word
from app.services.position_match.spec import CandidateSource, MatchSpec, SlotConstraint
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.position_match.mask_adapter import (
    mask_char_glob_pattern,
    mask_fixed_literal_prefix,
    matches_mask_literal_chars,
    required_codes_from_spec,
)
from app.services.word_serializer import get_word_jyutping, get_word_sort_code, get_word_text
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import (
    get_mask_index_candidates,
    get_phoneme_index_candidates,
    get_words_for_length,
    is_word_cache_ready,
)
from app.services._generated.candidate_source_policy import CANDIDATE_FALLBACK_LIMIT


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
    fallback_limit: Optional[int] = CANDIDATE_FALLBACK_LIMIT

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
    required_codes: Optional[list[Optional[str]]] = None

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        effective_mode = mode or self.mode
        effective_code = code if code is not None else self.query_code
        required_codes = self.required_codes or [None] * len(self.mask)

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
        # Cold DB: never materialize full length bucket (Portable hang on mask family)
        return (
            query.order_by(Word.char, Word.jyutping).limit(CANDIDATE_FALLBACK_LIMIT).all(),
            False,
        )


def get_length_candidates(
    db,
    width: int,
    mask: str,
    *,
    fallback_limit: Optional[int] = CANDIDATE_FALLBACK_LIMIT,
):
    """
    取得指定長度的候選詞，並對 cache 命中者先做 mask literal 預過濾。
    用於 rhyme-anchor、code-tail、at-tail 等需要 mask 的情境。
    fallback_limit=None → 語意完整候選宇宙（唔截斷）。
    """
    indexed = get_mask_index_candidates(width, mask)
    if indexed is not None:
        candidates = indexed
    else:
        candidates = get_words_for_length(width)
    if candidates:
        return [w for w in candidates if matches_mask_literal_chars(get_word_text(w), mask)], True
    glob_pat = mask_char_glob_pattern(mask)
    query = db.query(Word).filter(
        length_filter(width),
        Word.char.op("GLOB")(glob_pat),
    )
    prefix = mask_fixed_literal_prefix(mask)
    if prefix:
        query = query.filter(Word.char.like(f"{prefix}%"))
    query = query.order_by(Word.char, Word.jyutping)
    if fallback_limit is not None:
        query = query.limit(fallback_limit)
    return query.all(), False


def get_rhyme_anchor_length_candidates(
    db,
    width: int,
    mask: str,
    anchor_pos: int,
    anchor: str,
    constraint: str,
) -> tuple[list[Any], bool]:
    """韻／聲錨候選：音素索引優先；冷路徑必須語意完整候選宇宙（唔 LIMIT 再濾韻）。"""
    if is_word_cache_ready():
        rows = get_phoneme_index_candidates(width, anchor_pos, anchor, constraint, db)
        narrowed = [
            w for w in rows
            if matches_mask_literal_chars(get_word_text(w), mask)
        ]
        return narrowed, True
    # Cold: mask GLOB without CANDIDATE_FALLBACK_LIMIT — phoneme filter runs in apply_match_spec.
    # (Repro: 就= with cache cold missed 后／就 when LIMIT 2000 before rhyme filter.)
    return get_length_candidates(db, width, mask, fallback_limit=None)


def get_candidates_for_length(
    db: Any,
    length: int,
    *,
    code: Optional[str] = None,
    mode: str = "m1",
    fallback_limit: Optional[int] = CANDIDATE_FALLBACK_LIMIT,
):
    """
    通用長度候選取得（無 mask 預過濾）。
    用於 hybrid 等情境。fallback_limit=None 表示唔截斷（碼夾 hybrid 需全桶）。
    """
    candidates = get_words_for_length(length)
    if candidates:
        return candidates, True
    query = db.query(Word).filter(length_filter(length))
    if code:
        query = apply_code_filter(query, code, mode)
    query = query.order_by(Word.char, Word.jyutping)
    if fallback_limit is not None:
        query = query.limit(fallback_limit)
    return query.all(), False


def _phoneme_anchor_slot(spec: MatchSpec) -> Optional[SlotConstraint]:
    for slot in spec.slots:
        if slot.kind in ("final_anchor", "initial_anchor"):
            return slot
    return None


def _compound_rhyme_char(spec: MatchSpec) -> Optional[str]:
    for slot in spec.slots:
        if slot.kind == "final_anchor" and isinstance(slot.value, str):
            return slot.value
    return None


@dataclass
class CompoundCandidateSource:
    """近義／反義／連接詞複合：字面容許集 + char IN；缺庫字面記憶體合成（ADR-0054）。"""

    db: Any
    compounds: frozenset[str]
    expected_length: int = 2
    allow_transient: bool = False

    def get_candidates(
        self,
        length: int,
        *,
        code: Optional[str] = None,
        mode: str = "m1",
    ) -> tuple[list[Any], bool]:
        if length != self.expected_length or not self.compounds:
            return [], True

        rows: list[Any] = []
        from_cache = False
        if is_word_cache_ready():
            rows = [
                w for w in get_words_for_length(self.expected_length)
                if get_word_text(w) in self.compounds
            ]
            from_cache = True
        if not rows:
            query = self.db.query(Word).filter(
                Word.char.in_(list(self.compounds)),
                length_filter(self.expected_length),
            )
            rows = query.order_by(Word.char, Word.code, Word.jyutping).all()
            from_cache = False

        if self.allow_transient:
            have = {get_word_text(w) for w in rows}
            missing = [ch for ch in self.compounds if ch not in have]
            if missing:
                from app.domain.relations.compound_connect import compose_transient_word

                for ch in missing:
                    transient = compose_transient_word(ch)
                    if transient is not None:
                        rows.append(transient)

        return rows, from_cache


CompoundSynCandidateSource = CompoundCandidateSource
CompoundAntCandidateSource = CompoundCandidateSource


def _resolve_mask_family_source(
    spec: MatchSpec,
    db: Any,
    mode: str,
    query_code: Optional[str],
) -> tuple[Optional[CandidateSource], Optional[Callable]]:
    """由 MatchSpec 形狀選擇候選來源（registry，不依 ParsedQuery）。"""
    from app.domain.lexicon.ranking import search_result_sort_key

    connective = spec.extra.get("connective")
    if spec.compound_kind == "doubled_syllable":
        rhyme_char = _compound_rhyme_char(spec)
        from app.domain.relations.compound_doubled_syllable import search_doubled_syllable

        tiers = search_doubled_syllable(db, rhyme_char=rhyme_char, width=spec.width)
        if not tiers:
            return None, None
        source = CompoundCandidateSource(
            db, frozenset(tiers.keys()), expected_length=spec.width
        )
        sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
        return source, sort_key

    if spec.compound_kind == "syn":
        rhyme_char = _compound_rhyme_char(spec)
        if connective and spec.width == 3:
            from app.domain.relations.compound_connect import search_connective_compound

            tiers = search_connective_compound(
                db,
                compound_kind="syn",
                connective=connective,
                rhyme_char=rhyme_char,
            )
            if not tiers:
                return None, None
            source = CompoundCandidateSource(
                db,
                frozenset(tiers.keys()),
                expected_length=3,
                allow_transient=True,
            )
            sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
            return source, sort_key

        from app.domain.relations.compound_syn import search_compound_syn

        tiers = search_compound_syn(db, rhyme_char=rhyme_char, width=spec.width)
        if not tiers:
            return None, None
        source = CompoundCandidateSource(db, frozenset(tiers.keys()))
        sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
        return source, sort_key

    if spec.compound_kind == "ant":
        rhyme_char = _compound_rhyme_char(spec)
        if connective and spec.width == 3:
            from app.domain.relations.compound_connect import search_connective_compound

            tiers = search_connective_compound(
                db,
                compound_kind="ant",
                connective=connective,
                rhyme_char=rhyme_char,
            )
            if not tiers:
                return None, None
            source = CompoundCandidateSource(
                db,
                frozenset(tiers.keys()),
                expected_length=3,
                allow_transient=True,
            )
            sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
            return source, sort_key

        from app.domain.relations.compound_ant import search_compound_ant

        tiers = search_compound_ant(db, rhyme_char=rhyme_char, width=spec.width)
        if not tiers:
            return None, None
        source = CompoundCandidateSource(db, frozenset(tiers.keys()))
        sort_key = lambda w: (tiers.get(get_word_text(w), 99), search_result_sort_key(w))
        return source, sort_key

    if spec.literal_priority and spec.mask:
        from app.services.position_match.mask_adapter import dense_code_from_spec

        effective_code = query_code or dense_code_from_spec(spec)
        source = MaskWildcardCandidateSource(
            db,
            spec.mask,
            mode=mode,
            query_code=effective_code,
            required_codes=required_codes_from_spec(spec),
        )
        literal_positions = spec.extra.get("literal_positions", [])
        sort_key = lambda w: literal_priority_sort_key(w, literal_positions)
        return source, sort_key

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

    # TS parity (specNeedsFullLengthBucket): letter slots need full bucket —
    # LengthMaskCandidateSource(??) + 2000 LIMIT truncates before letter filter
    # (repro: 43$獅 → 43si misses 舞獅).
    has_letter_slots = any(
        s.kind in ("rhyme_letters", "syllable_letters", "initial_letters")
        for s in spec.slots
    )
    if has_letter_slots:
        from app.services.position_match.mask_adapter import dense_code_from_spec

        effective_code = query_code or dense_code_from_spec(spec)
        return (
            LengthCodeCandidateSource(
                db,
                code=effective_code,
                mode=mode,
                fallback_limit=None,
            ),
            None,
        )

    if spec.mask:
        from app.services.position_match.mask_adapter import dense_code_from_spec

        # Full-width dense code: load complete code bucket (no LIMIT 2000 + ORDER BY char).
        # Repro: workbench 貪婪 same_tone → code 30; 金錢 high essay but late alpha → dropped.
        effective_code = query_code or dense_code_from_spec(spec)
        if (
            effective_code
            and len(effective_code) == spec.width
            and effective_code.isdigit()
        ):
            return (
                LengthCodeCandidateSource(
                    db,
                    code=effective_code,
                    mode=mode,
                    fallback_limit=None,
                ),
                None,
            )
        return LengthMaskCandidateSource(db, spec.mask), None

    return None, None