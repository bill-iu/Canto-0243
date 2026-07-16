"""Explain IR render — structural IR → human summary (ADR-0021)."""
from __future__ import annotations

from typing import Any

_CN_WIDTH = ("", "一", "兩", "三", "四", "五", "六", "七", "八", "九", "十")
_RHYME_LABELS = ("", "單押", "雙押", "三押", "四押")


def render_explain_ir(ir: dict[str, Any]) -> str:
    variant = ir["variant"]
    if variant == "whole_word_equals":
        return _render_whole_word_equals(ir)
    if variant == "prefix_wildcard_equals":
        return _render_prefix_wildcard_equals(ir)
    if variant == "code_sandwich_whole_word":
        return _render_code_sandwich_whole_word(ir)
    if variant == "code_sandwich_scan":
        return _render_code_sandwich_scan(ir)
    if variant == "compound":
        return _render_compound(ir)
    if variant == "slot_scan":
        return _render_slot_scan(ir)
    return _width_label(ir.get("width", 1))


def _word_pos(n: int) -> str:
    return f"第 {n + 1} 個字"


def _width_label(width: int) -> str:
    cn = _CN_WIDTH[width] if width < len(_CN_WIDTH) else str(width)
    return f"{cn}個字"


def _rhyme_label(n: int) -> str:
    if n < len(_RHYME_LABELS):
        return _RHYME_LABELS[n]
    return f"{n}押"


def _rhyme_or_initial(dimension: str) -> str:
    return "同韻" if dimension == "final" else "同聲"


def _pos_list_label(positions: list[int]) -> str:
    if len(positions) == 1:
        return _word_pos(positions[0])
    nums = "、".join(f"第 {p + 1}" for p in positions)
    return f"{nums} 個字"


def _render_code_prefix_phrase(code_prefix: dict[str, Any]) -> str:
    digits = code_prefix["digits"]
    if code_prefix["per_digit_full"]:
        parts = [
            f"{_word_pos(i)}同 {digit} 同音"
            for i, digit in enumerate(digits)
        ]
        return "，".join(parts)
    return f"前 {len(digits)} 個字為碼 {digits}"


def _render_whole_word_equals(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    line = f"整詞同「{equals['ref_literal']}」{dim}（{label}）"
    code_prefix = ir.get("code_prefix")
    if code_prefix:
        return f"{line}；{_render_code_prefix_phrase(code_prefix)}"
    return line


def _render_prefix_wildcard_equals(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    positions = list(range(equals["start_pos"], ir["width"]))
    pos_label = _pos_list_label(positions)
    return (
        f"首個字任意；{pos_label}同「{equals['ref_literal']}」{dim}（{label}）"
    )


def _render_code_sandwich_whole_word(ir: dict[str, Any]) -> str:
    equals = ir["equals"]
    dim = _rhyme_or_initial(equals["dimension"])
    label = _rhyme_label(len(equals["ref_literal"]))
    rhyme_line = f"同「{equals['ref_literal']}」{dim}（{label}）"
    code_prefix = ir.get("code_prefix")
    body = rhyme_line if not code_prefix else f"{rhyme_line}；{_render_code_prefix_phrase(code_prefix)}"
    return f"數字夾字「{ir['raw_q']}」：{body}"


def _render_constraint_phrase(c: dict[str, Any]) -> str:
    pos = c["pos"]
    kind = c["kind"]
    label = _word_pos(pos)
    if kind == "code_digit":
        return f"{label}同 {c['digit']} 同音"
    if kind == "literal_char":
        return f"{label}為「{c['char']}」"
    if kind == "wildcard":
        return f"{label}任意字"
    if kind == "hybrid_tail_rhyme":
        return f"{label}同 {c['digit']} 同音且同「{c['ref']}」同韻"
    if kind == "hybrid_tail_initial":
        return f"{label}同 {c['digit']} 同音且同「{c['ref']}」同聲"
    if kind == "hybrid_code_literal":
        return f"{label}同 {c['digit']} 同音且限定為{c['ref']}"
    if kind == "final_anchor":
        return f"{label}同「{c['ref']}」同韻"
    if kind == "initial_anchor":
        return f"{label}同「{c['ref']}」同聲"
    if kind == "rhyme_letters":
        return f"{label}同韻母 {c['letters']}"
    if kind == "initial_letters":
        return f"{label}同聲母 {c['letters']}"
    if kind == "syllable_letters":
        return f"{label}粵拼音節 {c['letters']}"
    ref = c.get("ref", "")
    return f"{label}為「{ref}」"


def _render_constraints(constraints: list[dict[str, Any]]) -> str:
    return "，".join(_render_constraint_phrase(c) for c in constraints)


def _render_code_sandwich_scan(ir: dict[str, Any]) -> str:
    constraints = ir.get("constraints") or []
    if constraints:
        return f"數字夾字「{ir['raw_q']}」：{_render_constraints(constraints)}"
    return f"數字夾字「{ir['raw_q']}」"


def _render_compound(ir: dict[str, Any]) -> str:
    compound = ir["compound"]
    if compound["kind"] == "doubled_syllable":
        n = compound["width"]
        code = compound.get("code")
        rhyme = compound.get("tail_rhyme")
        base = f"查{n}字雙聲疊韻字（各字音節相同，聲調不限）"
        if code and rhyme:
            return f"查{n}字雙聲疊韻字（碼 {code}，尾字同「{rhyme}」同韻）"
        if code:
            return f"查{n}字雙聲疊韻字（碼 {code}）"
        if rhyme:
            return f"查{n}字雙聲疊韻字（尾字同「{rhyme}」同韻）"
        return base
    label = "近義" if compound["kind"] == "syn" else "反義"
    connective = compound.get("connective")
    if connective:
        return f"查詢含「{connective}」嘅{label}複合詞"
    return f"查詢{label}複合詞"


def _render_slot_scan(ir: dict[str, Any]) -> str:
    constraints = ir.get("constraints") or []
    if not constraints:
        return _width_label(ir["width"])
    return f"{_width_label(ir['width'])}：{_render_constraints(constraints)}"
