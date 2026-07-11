"""黃金查詢集 CI 子集 — enforce_bench + registry 代表查詢去重。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryJourneyCase:
    query: str
    mode: str = "m1"
    db: str = "fixture"  # fixture | memory | lyrics
    min_words: int = 0
    must_include: tuple[str, ...] = ()
    seed: str = ""
    parity: bool = True  # False for lyrics-only rows (fixture parity skips)


@dataclass(frozen=True)
class ParityCase:
    """PWA vs portable parity row — used by scripts/pwa_golden_parity.py."""

    query: str
    mode: str = "m1"
    db: str = "fixture"  # fixture | memory
    seed: str = ""
    ordered: bool = False
    suite: str = "journey"  # journey | match_spec


# enforce_bench critical + registry representatives; deduped ~19 (1 lyrics-gated)
GOLDEN_QUERY_JOURNEYS: tuple[QueryJourneyCase, ...] = (
    QueryJourneyCase("事業", "m1", min_words=1),
    QueryJourneyCase("事業", "m2", min_words=1),
    QueryJourneyCase("門0", "m1"),
    QueryJourneyCase("好23", "m1"),
    QueryJourneyCase("香港=", "m1", min_words=1),
    QueryJourneyCase("香=?", "m1"),
    QueryJourneyCase("23就", "m1"),
    QueryJourneyCase("23@手", "m1"),
    QueryJourneyCase("2=我3", "m1"),
    QueryJourneyCase(
        "39起",
        "m1",
        db="lyrics",
        must_include=("飛起", "飛機"),
        parity=False,
    ),
    QueryJourneyCase("2我=3", "m1"),
    QueryJourneyCase("23+就", "m1"),
    QueryJourneyCase("?困潦倒=", "m1"),
    QueryJourneyCase("33~~你", "m1"),
    QueryJourneyCase("33!!你", "m1"),
    QueryJourneyCase("$$", "m1"),
    QueryJourneyCase("$$$", "m1"),
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
    QueryJourneyCase("開心", "syn", db="memory", seed="relation_syn", min_words=1, must_include=("愉快",)),
    QueryJourneyCase("ming4", "syn", db="memory", seed="relation_syn"),
)


MATCH_SPEC_REPRESENTATIVE_CASES: tuple[tuple[str, dict], ...] = (
    ("香港=", {"width": 2, "ref_literal": "香港", "whole_word": True}),
    ("?困潦倒=", {"width": 4, "prefix_wildcard": True}),
    ("04困=49倒=", {"width": 4, "anchor_count": 2}),
    ("23+就", {"width": 3, "code_prefix": "23"}),
    ("23@手", {"width": 2, "mask": "?手"}),
    ("就=", {"width": 1, "anchor": "就"}),
    ("?yut?", {"width": 3, "jyutping_slot": True}),
    ("3m4", {"width": 2, "dual_phoneme": True}),
    ("23就", {"width": 2, "ref_literal": "就", "code_prefix": "23"}),
    ("39起", {"width": 2, "ref_literal": "起", "code_prefix": "39"}),
    ("門0", {"width": 2, "literal_priority": True}),
    ("33~~你", {"width": 2, "compound_kind": "syn", "code_prefix": "33"}),
    ("$$", {"width": 2, "compound_kind": "doubled_syllable"}),
    ("$$$", {"width": 3, "compound_kind": "doubled_syllable"}),
    ("33!!你", {"width": 2, "compound_kind": "ant", "code_prefix": "33"}),
    ("窮?潦倒=", {"width": 4, "partial_rhyme_mask": True, "anchor_count": 3}),
    ("=窮?潦倒", {"width": 4, "partial_initial_mask": True, "anchor_count": 3}),
)

# Journey gate: lookup layout + mask family ordering (now includes mask ranking + heteronym).
JOURNEY_ORDERED_QUERIES = frozenset({
  "事業",
  "門0",
  "23就",
  "23@手",
  "23+就",
  "?困潦倒=",
  "33~~你",
  "33!!你",
  "$$",
  "$$$",
  "窮?潦倒=",
  "香港=",
  "香=?",
})
# Match-spec baseline: ranked masks including literal_priority ordering.
MATCH_SPEC_ORDERED_QUERIES = frozenset({
  "香港=",
  "?困潦倒=",
  "04困=49倒=",
  "23+就",
  "23@手",
  "就=",
  "?yut?",
  "23就",
  "門0",
  "33~~你",
  "$$",
  "$$$",
  "33!!你",
  "窮?潦倒=",
  "=窮?潦倒",
})


def parity_cases_from_journeys() -> tuple[ParityCase, ...]:
    return tuple(
        ParityCase(
            query=c.query,
            mode=c.mode,
            db=c.db,
            seed=c.seed,
            ordered=c.query in JOURNEY_ORDERED_QUERIES,
            suite="journey",
        )
        for c in GOLDEN_QUERY_JOURNEYS
        if c.parity
    )


def parity_cases_from_match_spec() -> tuple[ParityCase, ...]:
    return tuple(
        ParityCase(
            query=q,
            mode="m1",
            db="fixture",
            ordered=q in MATCH_SPEC_ORDERED_QUERIES,
            suite="match_spec",
        )
        for q, _meta in MATCH_SPEC_REPRESENTATIVE_CASES
    )


PARITY_JOURNEY_CASES: tuple[ParityCase, ...] = parity_cases_from_journeys()
PARITY_MATCH_SPEC_CASES: tuple[ParityCase, ...] = parity_cases_from_match_spec()
ALL_PARITY_CASES: tuple[ParityCase, ...] = PARITY_JOURNEY_CASES + PARITY_MATCH_SPEC_CASES


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
    "MASK",
    "COMPOUND_SYN",
    "COMPOUND_DOUBLED_SYLLABLE",
    "COMPOUND_ANT",
    "PARTIAL_RHYME_MASK",
    "PARTIAL_INITIAL_MASK",
    "PING_ZE_SERIAL",
})
