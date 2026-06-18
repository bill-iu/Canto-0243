"""等號查詢 grammar stub（#3 下一輪；完整 equals 家族待搬）。"""
from __future__ import annotations

import re

from app.services.query_tokens import CODE_TAIL_MIDDLE

HYBRID_TAIL_EQUALS_RE = re.compile(r"^(\d+)([一-龥])=$")


def is_hybrid_tail_equals_alias(q: str) -> bool:
    """True for 23就= style queries that alias hybrid tail-rhyme (23就)."""
    return bool(HYBRID_TAIL_EQUALS_RE.match(q))


def hybrid_query_from_tail_equals(q: str) -> str:
    return q[:-1]


def is_framed_equals_query(q: str) -> bool:
    """Legacy framed equals: 香港=, 2=我3 — not query-level rhyme anchors or hybrid tail alias."""
    if CODE_TAIL_MIDDLE in q or "@" in q or is_hybrid_tail_equals_alias(q):
        return False
    match = re.match(r"^(\d*)(=)?([一-龥]+)(=)?(\d*)$", q)
    if not match:
        return False
    target = match.group(3) or ""
    if not target:
        return False
    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    if right_equal and len(target) >= 2:
        return True
    if right_equal and left_code and len(target) == 1:
        return True
    if inner_equal and left_code and right_code:
        return True
    if inner_equal and left_code and not right_equal:
        return True
    if inner_equal and not left_code and not right_code and len(target) >= 2:
        return True
    return False


def build_equals_match_spec(q: str):
    """查詢字串 → 等號 MatchSpec（純函式，無 DB）。語意見 CONTEXT § 碼夾等號查詢。"""
    from app.services.position_match import MatchSpec
    from app.services.position_match.spec import EqualsSpan

    match = re.match(r"^(\d*)(=)?([一-龥]+)?(=)?(\d*)$", q)
    if not match:
        return None
    target_str = match.group(3) or ""
    if not target_str:
        return None

    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    target_length = len(target_str)
    expected_length = len(left_code) + len(right_code) or target_length
    start_pos = max(0, len(left_code) - target_length)
    full_code = left_code + right_code

    span = EqualsSpan(
        ref_literal=target_str,
        start_pos=start_pos,
        dimension="final" if right_equal else "initial",
        phoneme_anchor_only=bool(left_code and (right_code or inner_equal)),
        whole_word=(start_pos == 0 and target_length == expected_length),
    )
    return MatchSpec(
        width=expected_length,
        code_prefix=full_code if full_code else None,
        extra={"equals_span": span},
    )


CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT = (
    "「{literal}」有收錄，但在 0243 碼 {code} 下無整詞同韻結果。"
)


def code_prefixed_whole_word_equals_empty_hint(spec, db) -> str | None:
    """左碼整詞等號零結果：參考詞有收錄但 code+整詞同韻無候選（CONTEXT § 等號查詢）。"""
    from app.lexicon.static_index import get_lexicon_entries
    from app.models.word import Word
    from app.services.position_match.spec import get_equals_span

    span = get_equals_span(spec)
    if not span or not span.whole_word:
        return None
    code = spec.code_prefix or ""
    literal = span.ref_literal
    if not code or len(code) != len(literal):
        return None
    catalogued = bool(get_lexicon_entries(literal)) or bool(
        db.query(Word).filter(Word.char == literal).first()
    )
    if not catalogued:
        return None
    return CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT.format(literal=literal, code=code)
