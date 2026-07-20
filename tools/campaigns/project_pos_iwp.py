"""Independent Word Probability (IWP) from Essay word-freq list.

Paper (Li et al.): IWP(c)=N(Word(c))/N(c) — fraction of times char c appears
as a standalone word vs all occurrences. High IWP ≈ free morpheme; low ≈ bound.

Here Essay is a word-frequency table (literal\\tfreq), so:
  N(Word(c)) = freq of unigram entry ``c``
  N(c) = sum_w freq(w) * count(c in w)
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

from tools.campaigns.project_pos_p1 import load_essay_ranked

DEFAULT_IWP_TSV = ROOT / "data" / "pos" / "iwp_char.tsv"
# Paper a=0.55 for pruning true singles out of fragments
DEFAULT_FREE_THRESHOLD = 0.55

_cache: Optional[Dict[str, float]] = None
_cache_counts: Optional[Tuple[Dict[str, int], Dict[str, int]]] = None


def compute_iwp_maps(
    essay_ranked: Optional[list] = None,
) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, int]]:
    """Return (iwp, n_word, n_char)."""
    ranked = essay_ranked if essay_ranked is not None else load_essay_ranked()
    n_word: Dict[str, int] = {}
    n_char: Dict[str, int] = {}
    for lit, freq in ranked:
        if not lit or freq <= 0:
            continue
        if len(lit) == 1:
            n_word[lit] = n_word.get(lit, 0) + freq
        for ch in lit:
            n_char[ch] = n_char.get(ch, 0) + freq
    iwp: Dict[str, float] = {}
    for ch, nc in n_char.items():
        if nc <= 0:
            continue
        iwp[ch] = n_word.get(ch, 0) / nc
    return iwp, n_word, n_char


def load_iwp(*, recompute: bool = False, cache_path: Path = DEFAULT_IWP_TSV) -> Dict[str, float]:
    """Load IWP map; compute+cache if missing."""
    global _cache
    if _cache is not None and not recompute:
        return _cache
    if cache_path.is_file() and not recompute:
        out: Dict[str, float] = {}
        with cache_path.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                ch = (r.get("char") or "").strip()
                if not ch:
                    continue
                try:
                    out[ch] = float(r.get("iwp") or 0)
                except ValueError:
                    continue
        _cache = out
        return out
    iwp, n_word, n_char = compute_iwp_maps()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["char", "iwp", "n_word", "n_char"],
            delimiter="\t",
            lineterminator="\n",
        )
        w.writeheader()
        for ch in sorted(iwp.keys(), key=lambda c: (-iwp[c], c)):
            w.writerow(
                {
                    "char": ch,
                    "iwp": f"{iwp[ch]:.6f}",
                    "n_word": n_word.get(ch, 0),
                    "n_char": n_char.get(ch, 0),
                }
            )
    _cache = iwp
    return iwp


def iwp_of(ch: str, iwp_map: Optional[Dict[str, float]] = None) -> float:
    m = iwp_map if iwp_map is not None else load_iwp()
    if len(ch) != 1:
        return 0.0
    return float(m.get(ch, 0.0))


def is_free_morpheme(ch: str, *, threshold: float = DEFAULT_FREE_THRESHOLD, iwp_map: Optional[Dict[str, float]] = None) -> bool:
    return iwp_of(ch, iwp_map) >= threshold


def _essay_freq(lit: str) -> int:
    from tools.campaigns.project_pos_p1 import load_essay_ranked

    # small module-level cache
    global _essay_freq_map
    if "_essay_freq_map" not in globals() or _essay_freq_map is None:
        _essay_freq_map = dict(load_essay_ranked())
    return int(_essay_freq_map.get(lit, 0))


_essay_freq_map: Optional[Dict[str, int]] = None
_n_char_map: Optional[Dict[str, int]] = None


def _n_char(ch: str) -> int:
    global _n_char_map
    if _n_char_map is None:
        # from cache file if present
        if DEFAULT_IWP_TSV.is_file():
            _n_char_map = {}
            with DEFAULT_IWP_TSV.open(encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh, delimiter="\t"):
                    c = (r.get("char") or "").strip()
                    if c:
                        try:
                            _n_char_map[c] = int(r.get("n_char") or 0)
                        except ValueError:
                            pass
        else:
            _, _, nc = compute_iwp_maps()
            _n_char_map = nc
    return int((_n_char_map or {}).get(ch, 0))


def residual_score(
    src: str,
    target: str,
    *,
    target_formal: bool,
    iwp_map: Optional[Dict[str, float]] = None,
) -> Tuple[float, str]:
    """Higher = better residual candidate. Returns (score, note).

    Combines: formal target, low IWP(src), affinity freq(target)/N(src).
    High affinity = char mass concentrated in this compound (true residual-ish).
    """
    m = iwp_map if iwp_map is not None else load_iwp()
    iwp_s = iwp_of(src, m)
    other = ""
    if len(target) == 2 and src in target:
        other = target[0] if target[1] == src else target[1] if target[0] == src else ""
    iwp_o = iwp_of(other, m) if other else 0.5
    base = 1.0 if target_formal else 0.35
    bound = max(0.0, 1.0 - iwp_s)
    nc = _n_char(src)
    tf = _essay_freq(target)
    affinity = (tf / nc) if nc > 0 else 0.0
    affinity = min(1.0, affinity)
    # free morpheme: hard demote
    if iwp_s >= DEFAULT_FREE_THRESHOLD:
        score = base * 0.05 * bound * (0.2 + 0.8 * affinity)
        note = f"iwp_src={iwp_s:.3f};aff={affinity:.3f};free-morpheme"
    else:
        # productive bound morpheme (潔/顯) has low IWP but low affinity → demote
        score = base * (0.15 + 0.55 * bound) * (0.2 + 0.8 * affinity)
        if other and iwp_o >= DEFAULT_FREE_THRESHOLD and affinity >= 0.2:
            score *= 1.1
        note = f"iwp_src={iwp_s:.3f};aff={affinity:.3f}"
        if other:
            note += f";iwp_other={iwp_o:.3f}"
    note += ";needs human apply"
    return round(min(score, 1.5), 4), note


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_iwp")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="recompute iwp_char.tsv from Essay")
    b.add_argument("--force", action="store_true")
    q = sub.add_parser("lookup", help="print IWP for chars")
    q.add_argument("chars", nargs="+")
    args = p.parse_args(argv)
    if args.cmd == "build":
        m = load_iwp(recompute=True)
        print(json.dumps({"chars": len(m), "out": str(DEFAULT_IWP_TSV)}, ensure_ascii=False))
        return 0
    if args.cmd == "lookup":
        m = load_iwp()
        for ch in args.chars:
            for c in ch:
                print(f"{c}\t{iwp_of(c, m):.6f}\tfree={is_free_morpheme(c, iwp_map=m)}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
