#!/usr/bin/env python3
"""Reproduce Wikidata P461 ∩ lyrics.db intersection (research probe).

Expects prior WDQS downloads under data/syn_ant/raw/wikidata/:
  edges.json, labels_zh-hant.json, labels_zh-tw.json, labels_zh-hk.json

Re-fetch tip (curl + User-Agent), see docs/research/2026-07-14-wikidata-opposite-of-zh-labels.md §10.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "syn_ant" / "raw" / "wikidata"
PREF = ("zh-hant", "zh-tw", "zh-hk")
CJK_LAB = re.compile(r"^[\u4e00-\u9fff]{1,6}$")
CJK_SPLIT = re.compile(r"[^\u4e00-\u9fff]+")
NOISE = re.compile(
    r"(黨|主義|帝國|政權|科學|軟體|硬體|洲|目$|科$|屬$|國$|省|縣|市|公法|私法|數學|複數|實數|偶蹄|奇蹄)"
)
ZOD = set("鼠牛虎兔龍蛇馬羊猴雞狗豬")
STEM = set("子丑寅卯辰巳午未申酉戌亥")


def qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def load_bindings(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["results"]["bindings"]


def prefer_label(by_lang: dict[str, str]) -> str | None:
    for lang in PREF:
        lab = (by_lang.get(lang) or "").strip()
        if lab:
            return lab
    return None


def guotong_cjk_pairs(path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        parts = [p for p in CJK_SPLIT.split(raw) if p]
        for i, a in enumerate(parts):
            for b in parts[i + 1 :]:
                if a != b:
                    pairs.add(tuple(sorted((a, b))))
    return pairs


def project_pairs(path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.lower().startswith("head"):
            continue
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        a, b = cols[0].strip(), cols[1].strip()
        if a and b and a != b:
            pairs.add(tuple(sorted((a, b))))
    return pairs


def is_noise(a: str, b: str) -> bool:
    if NOISE.search(a + b):
        return True
    if len(a) == 1 and len(b) == 1:
        if a in ZOD and b in ZOD:
            return True
        if a in STEM or b in STEM:
            return True
    return False


def main() -> int:
    needed = ["edges.json", "labels_zh-hant.json", "labels_zh-tw.json", "labels_zh-hk.json"]
    missing = [n for n in needed if not (OUT / n).is_file()]
    if missing:
        print("missing:", ", ".join(missing), file=sys.stderr)
        print("download into", OUT, file=sys.stderr)
        return 1

    labels: dict[str, dict[str, str]] = defaultdict(dict)
    for lang in PREF:
        for r in load_bindings(OUT / f"labels_{lang}.json"):
            labels[qid(r["x"]["value"])][lang] = r["lab"]["value"]

    undirected: dict[tuple[str, str], tuple[str, str, str, str]] = {}
    for r in load_bindings(OUT / "edges.json"):
        qa, qb = qid(r["a"]["value"]), qid(r["b"]["value"])
        la, lb = prefer_label(labels.get(qa, {})), prefer_label(labels.get(qb, {}))
        if not la or not lb:
            continue
        undirected.setdefault(tuple(sorted((qa, qb))), (qa, la, qb, lb))

    lex = {
        row[0]
        for row in sqlite3.connect(ROOT / "lyrics.db").execute("SELECT DISTINCT char FROM words")
        if row[0]
    }
    guotong = guotong_cjk_pairs(ROOT / "data" / "thesaurus" / "dict_antonym.txt")
    project = project_pairs(ROOT / "data" / "syn_ant" / "project_antonyms.tsv")

    intersect = []
    for qa, la, qb, lb in undirected.values():
        if la == lb or not CJK_LAB.fullmatch(la) or not CJK_LAB.fullmatch(lb):
            continue
        if la not in lex or lb not in lex:
            continue
        key = tuple(sorted((la, lb)))
        intersect.append(
            {
                "a": la,
                "b": lb,
                "qid_a": qa,
                "qid_b": qb,
                "in_guotong": key in guotong,
                "in_project_ant": key in project,
            }
        )

    novel = [r for r in intersect if not r["in_guotong"] and not r["in_project_ant"]]
    kept = [r for r in novel if not is_noise(r["a"], r["b"])]
    stats = {
        "undirected_pref_labels": len(undirected),
        "intersect": len(intersect),
        "in_guotong_cjk": sum(1 for r in intersect if r["in_guotong"]),
        "in_project": sum(1 for r in intersect if r["in_project_ant"]),
        "novel": len(novel),
        "novel_kept": len(kept),
        "novel_kept_len_le2": sum(1 for r in kept if len(r["a"]) <= 2 and len(r["b"]) <= 2),
        "guotong_cjk_undirected": len(guotong),
        "lexicon_literals": len(lex),
        "kept_len_buckets": {
            f"{a}x{b}": c
            for (a, b), c in sorted(Counter((len(r["a"]), len(r["b"])) for r in kept).items())
        },
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    # assert floor so the probe fails if extract collapses
    assert stats["intersect"] >= 100, stats
    assert stats["novel_kept"] >= 50, stats
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
