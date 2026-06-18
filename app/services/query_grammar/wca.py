"""通配碼錨 grammar（#3 收尾）。"""
from __future__ import annotations

import re
from typing import Optional

from app.services.query_tokens import CANTO_CHARS_RE, CODE_TAIL_MIDDLE, is_wildcard_char

_PLUS = re.escape(CODE_TAIL_MIDDLE)


def _tokenize(body: str) -> Optional[list[tuple[str, str]]]:
    tokens: list[tuple[str, str]] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if is_wildcard_char(ch):
            tokens.append(("wild", ch))
            i += 1
        elif ch == CODE_TAIL_MIDDLE:
            tokens.append(("star", ""))
            i += 1
        elif ch.isdigit():
            while i < len(body) and body[i].isdigit():
                tokens.append(("code", body[i]))
                i += 1
        elif CANTO_CHARS_RE.match(ch):
            tokens.append(("ref", ch))
            i += 1
        else:
            return None
    return tokens or None


def _tokens_to_spec(
    tokens: list[tuple[str, str]], *, head_literal: Optional[str] = None
) -> Optional[dict]:
    syllables: list[dict] = []
    if head_literal:
        syllables.append({"literal": head_literal})
    i = 0
    while i < len(tokens):
        kind, val = tokens[i]
        if kind == "wild":
            syllables.append({"wild": True})
            i += 1
        elif kind == "code":
            syllables.append({"code": val})
            i += 1
        elif kind == "star":
            if i + 1 < len(tokens) and tokens[i + 1][0] == "ref":
                syllables.append({"ref": tokens[i + 1][1], "star_before": True})
                i += 2
            else:
                syllables.append({"wild": True})
                i += 1
        elif kind == "ref":
            if syllables and "code" in syllables[-1] and "ref" not in syllables[-1]:
                syllables[-1]["ref"] = val
                i += 1
            else:
                return None
        else:
            return None
    if not syllables:
        return None
    if not any("code" in s for s in syllables) or not any("ref" in s for s in syllables):
        return None
    if head_literal is None and not (tokens and tokens[0][0] == "wild"):
        return None
    slots: list[dict] = []
    for pos, syl in enumerate(syllables):
        if "literal" in syl:
            slots.append({"pos": pos, "kind": "literal_char", "value": syl["literal"]})
        if "code" in syl:
            slots.append({"pos": pos, "kind": "code_digit", "value": syl["code"]})
        if "ref" in syl:
            slots.append({"pos": pos, "kind": "final_anchor", "value": syl["ref"]})
    return {"width": len(syllables), "slots": slots, "head_literal": head_literal}


def parse_wildcard_code_anchor_query(q: str) -> Optional[dict]:
    """通配碼錨：?30人、?30+人、+香?30人（左至右掃描）。"""
    if not q or "@" in q or "=" in q:
        return None
    if re.match(rf"^\d+{_PLUS}", q):
        return None
    m = re.match(rf"^{_PLUS}([一-龥])([?_%][0-9_?%{_PLUS}一-龥]+)$", q)
    if m:
        tokens = _tokenize(m.group(2))
        if not tokens:
            return None
        spec = _tokens_to_spec(tokens, head_literal=m.group(1))
        if spec:
            spec["raw_q"] = q
        return spec
    if q[0] not in "?_%":
        return None
    tokens = _tokenize(q)
    if not tokens:
        return None
    spec = _tokens_to_spec(tokens)
    if spec:
        spec["raw_q"] = q
    return spec


def looks_like_wildcard_code_anchor_query(q: str) -> bool:
    return parse_wildcard_code_anchor_query(q) is not None
