"""近反義 relation grammar（#3 收尾）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services._generated.fillword_connectives import FILLWORD_CONNECTIVES_STR

RELATION_LOOKUP_RE = re.compile(r"^(\d*)([~!])([\u4e00-\u9fff]+)$")
COMPOUND_CONNECT_ANT_RE = re.compile(
    rf"^(\d*)!([{FILLWORD_CONNECTIVES_STR}])!([\u4e00-\u9fff])?$"
)
COMPOUND_CONNECT_SYN_RE = re.compile(
    rf"^(\d*)~([{FILLWORD_CONNECTIVES_STR}])~([\u4e00-\u9fff])?$"
)
COMPOUND_SYN_RE = re.compile(r"^(\d*)~~([\u4e00-\u9fff])?$")
COMPOUND_ANT_RE = re.compile(r"^(\d*)!!([\u4e00-\u9fff])?$")
COMPOUND_DOUBLED_SYLLABLE_RE = re.compile(r"^(\d*)(\$+)([\u4e00-\u9fff])?$")
DOUBLED_SYLLABLE_MIN_DOLLARS = 2
DOUBLED_SYLLABLE_MAX_DOLLARS = 4
DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT = "雙聲疊韻字查詢須用 2 至 4 個連續 $。"
DOUBLED_SYLLABLE_CODE_WIDTH_HINT = "碼位數須與 $ 個數一致（如 333$$$）。"


def parse_doubled_syllable_syntax(q: str) -> Optional[dict]:
    m = COMPOUND_DOUBLED_SYLLABLE_RE.match(q)
    if not m:
        return None
    dollars = m.group(2) or ""
    width = len(dollars)
    if width < DOUBLED_SYLLABLE_MIN_DOLLARS or width > DOUBLED_SYLLABLE_MAX_DOLLARS:
        return {"kind": "doubled_syllable_invalid", "hint": DOUBLED_SYLLABLE_DOLLAR_COUNT_HINT}
    prefix = m.group(1) or ""
    if prefix and len(prefix) != width:
        return {"kind": "doubled_syllable_invalid", "hint": DOUBLED_SYLLABLE_CODE_WIDTH_HINT}
    rhyme_char = m.group(3) or None
    return {
        "kind": "compound_doubled_syllable",
        "code_prefix": prefix or None,
        "rhyme_char": rhyme_char,
        "width": width,
    }


def parse_relation_syntax(q: str) -> Optional[dict]:
    """Parse 0243 relation syntax: connective compound, ~~/!!, ~syn, !ant."""
    connect_syn = COMPOUND_CONNECT_SYN_RE.match(q)
    if connect_syn:
        prefix = connect_syn.group(1) or ""
        rhyme_char = connect_syn.group(3) or None
        return {
            "kind": "compound_connect_syn",
            "code_prefix": prefix or None,
            "connective": connect_syn.group(2),
            "rhyme_char": rhyme_char,
        }

    connect_ant = COMPOUND_CONNECT_ANT_RE.match(q)
    if connect_ant:
        prefix = connect_ant.group(1) or ""
        rhyme_char = connect_ant.group(3) or None
        return {
            "kind": "compound_connect_ant",
            "code_prefix": prefix or None,
            "connective": connect_ant.group(2),
            "rhyme_char": rhyme_char,
        }

    compound_syn = COMPOUND_SYN_RE.match(q)
    if compound_syn:
        prefix = compound_syn.group(1) or ""
        rhyme_char = compound_syn.group(2) or None
        return {
            "kind": "compound_syn",
            "code_prefix": prefix or None,
            "rhyme_char": rhyme_char,
        }

    compound = COMPOUND_ANT_RE.match(q)
    if compound:
        prefix = compound.group(1) or ""
        rhyme_char = compound.group(2) or None
        return {
            "kind": "compound_ant",
            "code_prefix": prefix or None,
            "rhyme_char": rhyme_char,
        }

    lookup = RELATION_LOOKUP_RE.match(q)
    if lookup:
        prefix = lookup.group(1) or ""
        op = lookup.group(2)
        word = lookup.group(3)
        return {
            "kind": "syn" if op == "~" else "ant",
            "code_prefix": prefix or None,
            "word": word,
        }
    return None


def to_match_spec(parsed):
    """ParsedQuery → MatchSpec for relation-family kinds (~~/!!/connect/$)."""
    from app.services.position_match import MatchSpec, SlotConstraint
    from app.services.position_match.mask_adapter import append_code_digit_slots
    from app.services.query_types import (
        CompoundAntQuery,
        CompoundConnectAntQuery,
        CompoundConnectSynQuery,
        CompoundDoubledSyllableQuery,
        CompoundSynQuery,
        QueryKind,
    )

    if isinstance(parsed, CompoundSynQuery) and parsed.kind == QueryKind.COMPOUND_SYN:
        spec = MatchSpec(width=2, compound_kind="syn")
        append_code_digit_slots(spec, parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(pos=1, kind="final_anchor", value=parsed.rhyme_char)
            )
        return spec

    if isinstance(parsed, CompoundAntQuery) and parsed.kind == QueryKind.COMPOUND_ANT:
        spec = MatchSpec(width=2, compound_kind="ant")
        append_code_digit_slots(spec, parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(pos=1, kind="final_anchor", value=parsed.rhyme_char)
            )
        return spec

    if isinstance(parsed, CompoundConnectSynQuery):
        spec = MatchSpec(width=3, compound_kind="syn")
        spec.extra["connective"] = parsed.connective
        append_code_digit_slots(spec, parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(pos=2, kind="final_anchor", value=parsed.rhyme_char)
            )
        return spec

    if isinstance(parsed, CompoundConnectAntQuery):
        spec = MatchSpec(width=3, compound_kind="ant")
        spec.extra["connective"] = parsed.connective
        append_code_digit_slots(spec, parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(pos=2, kind="final_anchor", value=parsed.rhyme_char)
            )
        return spec

    if isinstance(parsed, CompoundDoubledSyllableQuery):
        spec = MatchSpec(width=parsed.width, compound_kind="doubled_syllable")
        append_code_digit_slots(spec, parsed.code_prefix)
        if parsed.rhyme_char:
            spec.slots.append(
                SlotConstraint(
                    pos=parsed.width - 1, kind="final_anchor", value=parsed.rhyme_char
                )
            )
        return spec

    return None
