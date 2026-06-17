from __future__ import annotations

import re
from typing import Optional

WILDCARD_CHARS = frozenset("_?%")
CODE_TAIL_MIDDLE = "*"
LEGACY_CODE_TAIL_SEPARATORS = ("&", "\u00b7")

CODE_TAIL_RE = re.compile(rf"^(\d+){re.escape(CODE_TAIL_MIDDLE)}(.+)$")

CONSECUTIVE_SLOT_CONNECTOR_HINT = (
    "唔支援連續 `*`／`+`：通配音節請用 `?`，slot 連接符最多一個。"
    "例：`?30?+人`（唔好寫 `?30++人`）。"
)
DIGIT_AFTER_SLOT_CONNECTOR_HINT = (
    "`*`／`+` 後須接漢字或粵拼錨，唔可以接碼。"
    "例：尾格用 `2*好3` 或 `2*好人`。"
)
HYBRID_TAIL_EQUALS_RE = re.compile(r"^(\d+)([一-龥])=$")
AT_TAIL_RE = re.compile(r"^(\d+)@([一-龥])$")
SLOT_CHARS_RE = r"[0-9_?%]"
_CANTO_CHARS_RE = re.compile(r"[\u4e00-\u9fff]")

RELATION_LOOKUP_RE = re.compile(r"^(\d*)([~!])([\u4e00-\u9fff]+)$")
FILLWORD_CONNECTIVES = "與和或共同及跟而且並向"
COMPOUND_CONNECT_ANT_RE = re.compile(
    rf"^(\d*)!([{FILLWORD_CONNECTIVES}])!([\u4e00-\u9fff])?$"
)
COMPOUND_CONNECT_SYN_RE = re.compile(
    rf"^(\d*)~([{FILLWORD_CONNECTIVES}])~([\u4e00-\u9fff])?$"
)
COMPOUND_SYN_RE = re.compile(r"^(\d*)~~([\u4e00-\u9fff])?$")
COMPOUND_ANT_RE = re.compile(r"^(\d*)!!([\u4e00-\u9fff])?$")


def normalize_code_tail_separators(q: str) -> str:
    """Map legacy code-tail separators (&, ·) to * only at digit-prefix positions."""
    m = re.match(r"^(\d+)([&·*])(.+)$", q)
    if not m:
        return q
    sep = m.group(2)
    if sep in LEGACY_CODE_TAIL_SEPARATORS:
        return f"{m.group(1)}{CODE_TAIL_MIDDLE}{m.group(3)}"
    return q


def normalize_query_syntax(q: str) -> str:
    """Full-width relation/wildcard punctuation → ASCII (查詢分派入口)."""
    q = q.replace("＊", "*").replace("﹡", "*")
    q = q.replace("＋", "+")
    q = q.replace("+", "*")
    q = q.replace("！！", "!!").replace("～～", "~~")
    return q.replace("！", "!").replace("～", "~").replace("？", "?")


def normalize_jyutping_slot_connectors(q: str) -> str:
    """ADR-0013：缺字型粵拼錨 slot 連接符規範化（?hon→?*hon、3?ngo4→3*ngo4）。"""
    if not q or re.search(_CANTO_CHARS_RE, q):
        m = re.match(r"^(\d)\?([a-zA-Z]+)(\d)$", q)
        if m:
            return f"{m.group(1)}*{m.group(2)}{m.group(3)}"
        return q
    m = re.match(r"^(\?)([a-zA-Z]+)(\?)$", q)
    if m and "*" not in q:
        return f"?*{m.group(2)}?"
    m = re.match(r"^(\?)([a-zA-Z]+)$", q)
    if m and "*" not in q:
        return f"?*{m.group(2)}"
    m = re.match(r"^(\d)\?([a-zA-Z]+)(\d)$", q)
    if m:
        return f"{m.group(1)}*{m.group(2)}{m.group(3)}"
    return q


def slot_connector_syntax_error(q: str) -> Optional[str]:
    """連續 ** 或 * 後接碼 → hint 文案。"""
    if "**" in q:
        return CONSECUTIVE_SLOT_CONNECTOR_HINT
    if re.search(r"\*\d", q):
        return DIGIT_AFTER_SLOT_CONNECTOR_HINT
    return None


def normalize_search_query(q: str) -> str:
    """查詢分派入口：strip、code-tail、全形標點、星號槽規範化。"""
    q = normalize_query_syntax(normalize_code_tail_separators(q.strip()))
    q = normalize_jyutping_slot_connectors(q)
    q = normalize_redundant_single_char_rhyme(q)
    return normalize_canonical_star_query(q)


PURE_CHARS_SERIAL_HINT = (
    "每個 `{字}=`／`={字}` 前須有 0243 碼。"
    "例：`04困=49倒=`（唔好寫 `窮困=潦倒=`）。"
)
PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT = (
    "前綴通配等號查詢須以 `=` 結尾。"
    "例：`?困潦倒=`（唔好漏尾格 `=`）。"
)
_SERIAL_CHARSET_RE = re.compile(r"^[0-9?=一-龥]+$")


def normalize_redundant_single_char_rhyme(q: str) -> str:
    """?{單字}= → {單字}=（冗餘前導 ?）。"""
    m = re.match(r"^(\?)([一-龥])=$", q)
    if m:
        return f"{m.group(2)}="
    return q


def prefix_wildcard_equals_missing_eq_hint(q: str) -> Optional[str]:
    if re.fullmatch(r"\?[一-龥]{2,}", q):
        return PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT
    return None


def parse_pure_chars_serial_hint(q: str) -> Optional[str]:
    if not q or not re.fullmatch(r"[一-龥=]+", q):
        return None
    if re.fullmatch(r"[一-龥]=", q):
        return None
    if is_framed_equals_query(q):
        return None
    if re.search(r"(?<![0-9])([一-龥])=", q):
        return PURE_CHARS_SERIAL_HINT
    return None


def parse_prefix_wildcard_equals_query(q: str) -> Optional[dict]:
    m = re.fullmatch(r"\?([一-龥]{2,})=$", q)
    if not m:
        return None
    inner = f"{m.group(1)}="
    return {"raw_q": q, "inner_q": inner, "ref_literal": m.group(1), "width": len(m.group(1)) + 1}


def _scan_serial_phoneme(q: str, constraint: str) -> Optional[dict]:
    i = 0
    pos = 0
    code_slots: list[tuple[int, str]] = []
    anchors: list[tuple[int, str]] = []
    mask_chars: list[str] = []
    while i < len(q):
        ch = q[i]
        if ch == "?":
            mask_chars.append("?")
            pos += 1
            i += 1
            continue
        if ch.isdigit():
            if constraint == "final":
                m = re.match(r"^(\d)([一-龥])=(?=[0-9?=]|$)", q[i:])
            else:
                m = re.match(r"^(\d)=([一-龥])(?=[0-9?=]|$)", q[i:])
            if m:
                digit, anchor = m.group(1), m.group(2)
                code_slots.append((pos, digit))
                anchors.append((pos, anchor))
                mask_chars.append(digit)
                pos += 1
                i += len(m.group(0))
                continue
            code_slots.append((pos, ch))
            mask_chars.append(ch)
            pos += 1
            i += 1
            continue
        return None
    if not anchors:
        return None
    return {
        "width": pos,
        "constraint": constraint,
        "code_slots": code_slots,
        "anchors": anchors,
        "mask": "".join(mask_chars),
    }


def framed_equals_blocks_serial(q: str) -> bool:
    """碼夾／整詞等號唔走串列（G2）。"""
    if not is_framed_equals_query(q):
        return False
    m = re.match(r"^(\d*)(=)?([一-龥]+)(=)?(\d*)$", q)
    if not m:
        return False
    if m.group(2):
        return True
    if m.group(5):
        return True
    if m.group(4) and len(m.group(3)) >= 2:
        return True
    return False


def parse_serial_phoneme_anchor_query(q: str) -> Optional[dict]:
    if not q or not _SERIAL_CHARSET_RE.match(q):
        return None
    if CODE_TAIL_MIDDLE in q or "@" in q or "*" in q or "_" in q or "%" in q:
        return None
    if framed_equals_blocks_serial(q):
        return None
    if re.fullmatch(r"[一-龥]=", q):
        return None
    has_rhyme = bool(re.search(r"\d[一-龥]=", q))
    has_initial = bool(re.search(r"\d=[一-龥]", q))
    if has_rhyme and has_initial:
        return None
    constraint = "final" if has_rhyme else "initial"
    if not has_rhyme and not has_initial:
        return None
    parsed = _scan_serial_phoneme(q, constraint)
    if not parsed:
        return None
    parsed["raw_q"] = q
    return parsed


_HEAD_LITERAL_TAIL_RE = re.compile(r"[_?%0-9=]")
_MIDDLE_WILDCARD_BEFORE_CANTO_RE = re.compile(
    rf"(?<![0-9*])([{re.escape('?_')}%])([一-龥])(?!=)"
)
_RHYME_ANCHOR_SHAPE_RE = re.compile(
    rf"^(?:"
    rf"({SLOT_CHARS_RE}+)([一-龥])=$|"
    rf"([一-龥])=({SLOT_CHARS_RE}+)$|"
    rf"=([一-龥])({SLOT_CHARS_RE}+)$|"
    rf"({SLOT_CHARS_RE}+)=([一-龥])$"
    rf")"
)
_TRIPLE_RHYME_ANCHOR_SHAPE_RE = re.compile(rf"^({SLOT_CHARS_RE}+)([一-龥])=\?$")


def normalize_canonical_star_query(q: str) -> str:
    """P0：首格字面 *X…、通配左中格 ?*字…（碼左參考字、韻錨、等號查詢唔插 *）。"""
    if not q or "*" in q:
        return q
    if re.match(r"^\?([一-龥]{2,})=$", q):
        return q
    if re.match(r"^\?[一-龥]{2,}$", q):
        return q
    if (
        re.fullmatch(r"[一-龥=]+", q)
        and re.search(r"(?<![0-9])([一-龥])=", q)
        and not re.fullmatch(r"[一-龥]=", q)
    ):
        return q
    if _SERIAL_CHARSET_RE.match(q) and re.search(r"\d[一-龥]=", q):
        return q
    if is_framed_equals_query(q):
        return q
    if _RHYME_ANCHOR_SHAPE_RE.match(q) or _TRIPLE_RHYME_ANCHOR_SHAPE_RE.match(q):
        return q
    m = re.match(r"^([一-龥])(.+)$", q)
    if m:
        tail = m.group(2)
        if tail.startswith("="):
            return q
        if _HEAD_LITERAL_TAIL_RE.search(tail):
            return "*" + q
    return _MIDDLE_WILDCARD_BEFORE_CANTO_RE.sub(r"\1*\2", q)


def mask_from_canonical_star_query(q: str) -> Optional[str]:
    """`*` 規範缺字串 → 等價 mask（與 normalize 後首格／中格字面 MaskQuery 同一 MatchSpec）。"""
    if not q or "=" in q:
        return None
    m = re.match(r"^\*([一-龥][0-9_?%]+)$", q)
    if m:
        return m.group(1)
    m = re.match(r"^([_?%])\*([一-龥])([0-9_?%]*)$", q)
    if m:
        return m.group(1) + m.group(2) + m.group(3)
    return None


def _wca_tokenize(body: str) -> Optional[list[tuple[str, str]]]:
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
        elif _CANTO_CHARS_RE.match(ch):
            tokens.append(("ref", ch))
            i += 1
        else:
            return None
    return tokens or None


def _wca_tokens_to_spec(
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
    """通配碼錨：?30人、?30*人、*香?30人（左至右掃描）。"""
    if not q or "@" in q or "=" in q:
        return None
    if re.match(r"^\d+\*", q):
        return None
    m = re.match(r"^\*([一-龥])([?_%][0-9_?%*一-龥]+)$", q)
    if m:
        tokens = _wca_tokenize(m.group(2))
        if not tokens:
            return None
        spec = _wca_tokens_to_spec(tokens, head_literal=m.group(1))
        if spec:
            spec["raw_q"] = q
        return spec
    if q[0] not in "?_%":
        return None
    tokens = _wca_tokenize(q)
    if not tokens:
        return None
    spec = _wca_tokens_to_spec(tokens)
    if spec:
        spec["raw_q"] = q
    return spec


def looks_like_wildcard_code_anchor_query(q: str) -> bool:
    return parse_wildcard_code_anchor_query(q) is not None


def parse_code_ref_rhyme_contradiction_hint(q: str) -> Optional[str]:
    """?3人? 無 = → hint（P3）。"""
    m = re.match(r"^([?_%]+)(\d+)([一-龥])([?_%])$", q)
    if m and "=" not in q:
        d, ref = m.group(2), m.group(3)
        return f"碼位同參考字「{ref}」衝突：請改用 `?{d}{ref}=?` 標中格同韻。"
    return None


def parse_code_ref_middle_rhyme_query(q: str) -> Optional[dict]:
    """碼＋參考字＋通配（中格韻）：?3人=?（P3）。"""
    m = re.match(r"^([?_%]+)(\d+)([一-龥])=\?$", q)
    if not m:
        return None
    leading, digits, anchor = m.group(1), m.group(2), m.group(3)
    width = len(leading) + len(digits) + 1
    anchor_pos = len(leading) + len(digits) - 1
    slots: list[dict] = []
    for i, d in enumerate(digits):
        slots.append({"pos": len(leading) + i, "kind": "code_digit", "value": d})
    slots.append({"pos": anchor_pos, "kind": "final_anchor", "value": anchor})
    return {
        "raw_q": q,
        "width": width,
        "anchor": anchor,
        "anchor_pos": anchor_pos,
        "leading": leading,
        "digits": digits,
        "slots": slots,
    }


def parse_single_char_rhyme_anchor_query(q: str) -> Optional[dict]:
    """單字韻錨 就=（規範形；?就= normalize 後等價）。"""
    m = re.match(r"^([一-龥])=$", q)
    if not m:
        m = re.match(r"^([?_%])([一-龥])=$", q)
        if not m:
            return None
        anchor = m.group(2)
    else:
        anchor = m.group(1)
    return {"raw_q": q, "anchor": anchor, "width": 1, "anchor_pos": 0}


def parse_double_wildcard_rhyme_query(q: str) -> Optional[dict]:
    """二字韻錨 ?*就=（P2）。"""
    m = re.match(r"^([?_%])\*([一-龥])=$", q)
    if not m:
        return None
    return {
        "constraint": "final",
        "anchor": m.group(2),
        "anchor_pos": 1,
        "slots": m.group(1),
        "width": 2,
    }


def is_hybrid_tail_equals_alias(q: str) -> bool:
    """True for 23就= style queries that alias hybrid tail-rhyme (23就)."""
    return bool(HYBRID_TAIL_EQUALS_RE.match(q))


def hybrid_query_from_tail_equals(q: str) -> str:
    return q[:-1]


def is_wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in WILDCARD_CHARS


def parse_mask_query(mask: str) -> tuple[int, list[Optional[str]], list[tuple[int, str]]]:
    """Split mask into length, per-position code digits, and literal canto positions."""
    expected_len = len(mask)
    required_codes: list[Optional[str]] = [None] * expected_len
    literal_positions: list[tuple[int, str]] = []
    for idx, ch in enumerate(mask):
        if is_wildcard_char(ch):
            continue
        if ch.isdigit():
            required_codes[idx] = ch
            continue
        literal_positions.append((idx, ch))
    return expected_len, required_codes, literal_positions


def mask_char_glob_pattern(mask: str) -> str:
    """Build SQLite GLOB for Word.char: wildcard/digit slots -> ?, literals unchanged."""
    return "".join(
        "?" if (is_wildcard_char(ch) or ch.isdigit()) else ch
        for ch in mask
    )


def mask_fixed_literal_prefix(mask: str) -> str:
    """Leading literal run before first wildcard or code digit (for SQL prefix filter)."""
    prefix: list[str] = []
    for ch in mask:
        if is_wildcard_char(ch) or ch.isdigit():
            break
        prefix.append(ch)
    return "".join(prefix)


def matches_mask_literal_chars(word_char: str, mask: str) -> bool:
    """True when every non-wildcard, non-digit mask slot equals the word character."""
    if len(word_char) != len(mask):
        return False
    for idx, ch in enumerate(mask):
        if is_wildcard_char(ch) or ch.isdigit():
            continue
        if word_char[idx] != ch:
            return False
    return True


def looks_like_mask_query(q: str) -> bool:
    """True when q uses position mask syntax (digits / canto / wildcards)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q:
        return False
    if looks_like_wildcard_code_anchor_query(q):
        return False
    if parse_code_ref_middle_rhyme_query(q):
        return False
    if parse_code_ref_rhyme_contradiction_hint(q):
        return False
    if parse_single_char_rhyme_anchor_query(q):
        return False
    if parse_double_wildcard_rhyme_query(q):
        return False
    if parse_rhyme_anchor_query(q):
        return False
    if not re.match(r"^[0-9_?%一-龥]+$", q):
        return False
    has_wild = any(is_wildcard_char(c) for c in q)
    has_digit = any(c.isdigit() for c in q)
    has_canto = any(not c.isdigit() and not is_wildcard_char(c) for c in q)
    return has_wild or (has_digit and has_canto)


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
        return True  # 34=我：左碼 + 內嵌 = + 參考字，無右碼
    if inner_equal and not left_code and not right_code and len(target) >= 2:
        return True  # =香港：整詞同聲（與 香港= 整詞同韻對稱）
    return False


def parse_rhyme_anchor_query(q: str) -> Optional[dict]:
    """Query-level rhyme anchor: 香=? / ?*就= / =香? / ?=就 (no code-tail *)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q or is_framed_equals_query(q):
        return None
    if parse_single_char_rhyme_anchor_query(q) or parse_double_wildcard_rhyme_query(q):
        return None

    m = re.match(rf"^({SLOT_CHARS_RE}+)([一-龥])=$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^([一-龥])=({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^=([一-龥])({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^({SLOT_CHARS_RE}+)=([一-龥])$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }
    return None


def parse_triple_rhyme_anchor_query(q: str) -> Optional[dict]:
    """三格韻錨：?{參考字}=? — 中格韻母、前後通配。"""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q or is_framed_equals_query(q):
        return None
    if is_hybrid_tail_equals_alias(q):
        return None

    m = re.match(rf"^({SLOT_CHARS_RE}+)([一-龥])=(\?)$", q)
    if not m:
        return None
    leading, anchor, _trail = m.group(1), m.group(2), m.group(3)
    if not any(is_wildcard_char(c) for c in leading):
        return None
    anchor_pos = len(leading)
    width = anchor_pos + 2
    return {
        "anchor": anchor,
        "anchor_pos": anchor_pos,
        "width": width,
        "leading_slots": leading,
        "constraint": "final",
    }


def parse_code_tail_query(q: str) -> Optional[dict]:
    if CODE_TAIL_MIDDLE not in q:
        return None
    m = CODE_TAIL_RE.match(q)
    if not m:
        return None
    code_digits = m.group(1)
    tail = m.group(2)
    width = len(code_digits) + 1

    m2 = re.match(r"^([一-龥])=$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "final",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^=([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "initial",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "literal",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }
    return None


def parse_star_anchor_query(q: str) -> Optional[dict]:
    """
    Star-anchor family (綜合頭/中/尾格):

    - 尾格（既有）: {code}*{漢字}{可選 '='}  /  {code}*= {漢字}（同聲母，legacy）
    - 中格（新增）: {left_code}*{漢字}{可選 '='}{right_code}
    - 頭格（新增）: *{漢字}{可選 '='}{right_code}
    """
    if not q or CODE_TAIL_MIDDLE not in q or "@" in q:
        return None

    # 頭格：*門0 / *門=0
    m = re.match(r"^\*([一-龥])(=)?(\d+)$", q)
    if m:
        anchor, eq, right = m.group(1), m.group(2), m.group(3)
        width = 1 + len(right)
        anchor_pos = 0
        return {
            "width": width,
            "anchor_pos": anchor_pos,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": [(anchor_pos + 1 + i, d) for i, d in enumerate(right)],
            "code_prefix": None,
        }

    # 中格：2*就3 / 2*就=3 / 23*就45 / 23*就=45
    m = re.match(r"^(\d+)\*([一-龥])(=)?(\d+)$", q)
    if m:
        left, anchor, eq, right = m.group(1), m.group(2), m.group(3), m.group(4)
        anchor_pos = len(left)
        width = len(left) + 1 + len(right)
        code_slots = [(i, d) for i, d in enumerate(left)] + [
            (anchor_pos + 1 + i, d) for i, d in enumerate(right)
        ]
        return {
            "width": width,
            "anchor_pos": anchor_pos,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": code_slots,
            "code_prefix": None,
        }

    # 尾格：23*就 / 23*就=
    m = re.match(r"^(\d+)\*([一-龥])(=)?$", q)
    if m:
        code, anchor, eq = m.group(1), m.group(2), m.group(3)
        width = len(code) + 1
        return {
            "width": width,
            "anchor_pos": width - 1,
            "anchor": anchor,
            "constraint": "final" if eq else "literal",
            "code_slots": [(i, d) for i, d in enumerate(code)],
            "code_prefix": code,
        }

    # 尾格同聲母（legacy）：23*=就
    m = re.match(r"^(\d+)\*=([一-龥])$", q)
    if m:
        code, anchor = m.group(1), m.group(2)
        width = len(code) + 1
        return {
            "width": width,
            "anchor_pos": width - 1,
            "anchor": anchor,
            "constraint": "initial",
            "code_slots": [(i, d) for i, d in enumerate(code)],
            "code_prefix": code,
        }
    return None


def parse_at_tail_query(q: str) -> Optional[dict]:
    m = AT_TAIL_RE.match(q)
    if not m:
        return None
    return {
        "code_digits": m.group(1),
        "literal_char": m.group(2),
        "width": len(m.group(1)),
    }


def build_mask_from_slots(slots: str, width: int, anchor_pos: int) -> str:
    """Build a literal-mask string with anchor position as wildcard."""
    chars = ["?"] * width
    if anchor_pos == 0:
        for i, ch in enumerate(slots, start=1):
            chars[i] = ch
    else:
        for i, ch in enumerate(slots):
            chars[i] = ch
    return "".join(chars)


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