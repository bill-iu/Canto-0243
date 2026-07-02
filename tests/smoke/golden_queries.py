"""黃金查詢集 CI 子集 — enforce_bench + registry 代表查詢去重。"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QueryJourneyCase:
    query: str
    mode: str = "m1"
    db: str = "fixture"  # fixture | memory
    min_words: int = 0
    must_include: tuple[str, ...] = ()
    seed: str = ""


# enforce_bench critical + registry representatives; deduped ~18
GOLDEN_QUERY_JOURNEYS: tuple[QueryJourneyCase, ...] = (
    QueryJourneyCase("事業", "m1", min_words=1),
    QueryJourneyCase("事業", "m2", min_words=1),
    QueryJourneyCase("門0", "m1"),
    QueryJourneyCase("好23", "m1"),
    QueryJourneyCase("香港=", "m1", min_words=1),
    QueryJourneyCase("香=?", "m1"),
    QueryJourneyCase("23就", "m1"),
    QueryJourneyCase("23@就", "m1"),
    QueryJourneyCase("2=我3", "m1"),
    QueryJourneyCase("2我=3", "m1"),
    QueryJourneyCase("23+就", "m1"),
    QueryJourneyCase("?困潦倒=", "m1"),
    QueryJourneyCase("33~~你", "m1"),
    QueryJourneyCase("33!!你", "m1"),
    QueryJourneyCase("$$", "m1"),
    QueryJourneyCase("窮?潦倒=", "m1"),
    QueryJourneyCase(
        "34=我",
        "m1",
        db="memory",
        min_words=1,
        must_include=("好我",),
        seed="left_code",
    ),
    QueryJourneyCase("~開心", "syn", db="memory", seed="relation_syn"),
)


MATCH_SPEC_REPRESENTATIVE_CASES: tuple[tuple[str, dict], ...] = (
    ("香港=", {"width": 2, "ref_literal": "香港", "whole_word": True}),
    ("?困潦倒=", {"width": 4, "prefix_wildcard": True}),
    ("04困=49倒=", {"width": 4, "anchor_count": 2}),
    ("23+就", {"width": 3, "code_prefix": "23"}),
    ("23@就", {"width": 2, "mask": "?就"}),
    ("就=", {"width": 1, "anchor": "就"}),
    ("?yut?", {"width": 3, "jyutping_slot": True}),
    ("3m4", {"width": 2, "dual_phoneme": True}),
    ("23就", {"width": 2, "hybrid_ref": "就"}),
    ("門0", {"width": 2, "literal_priority": True}),
    ("33~~你", {"width": 2, "compound_kind": "syn", "code_prefix": "33"}),
    ("$$", {"width": 2, "compound_kind": "doubled_syllable"}),
    ("33!!你", {"width": 2, "compound_kind": "ant", "code_prefix": "33"}),
    ("窮?潦倒=", {"width": 4, "partial_rhyme_mask": True, "anchor_count": 3}),
    ("=窮?潦倒", {"width": 4, "partial_initial_mask": True, "anchor_count": 3}),
)

BUILDER_KINDS_WITH_REPRESENTATIVE_QUERY = frozenset({
    "EQUALS",
    "PREFIX_WILDCARD_EQUALS",
    "SERIAL_PHONEME",
    "PLUS_ANCHOR",
    "LITERAL_REF",
    "WILDCARD_CODE_ANCHOR",
    "CODE_REF_MIDDLE_RHYME",
    "RHYME_ANCHOR",
    "TRIPLE_RHYME_ANCHOR",
    "JYUTPING_ANCHOR",
    "HYBRID_CODE",
    "MASK",
    "COMPOUND_SYN",
    "COMPOUND_DOUBLED_SYLLABLE",
    "COMPOUND_ANT",
    "PARTIAL_RHYME_MASK",
    "PARTIAL_INITIAL_MASK",
})
