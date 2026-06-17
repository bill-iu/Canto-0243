"""近反義 relation grammar（#3 收尾）。"""
from __future__ import annotations

import re
from typing import Optional

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
