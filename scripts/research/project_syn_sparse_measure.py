"""專案自建近義：直連近義過稀（尾數＜2）freeze 前基線量度。

Run: python scripts/research/project_syn_sparse_measure.py
Writes JSON + Markdown under docs/research/.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import is_valid_term, normalize_literal  # noqa: E402
from app.lexicon.essay_index import get_essay_frequency, load_essay_corpus  # noqa: E402
from app.thesaurus.static_index import (  # noqa: E402
    get_cilin_synonyms,
    get_guotong_synonyms,
    load_cilin_index,
    load_thesaurus_dicts,
)

DB = ROOT / "client" / "public" / "lyrics.db"
OUT_JSON = ROOT / "docs" / "research" / "2026-07-18-project-syn-sparse-measure.json"
OUT_MD = ROOT / "docs" / "research" / "2026-07-18-project-syn-sparse-measure.md"
OUT_TOP_TSV = ROOT / "docs" / "research" / "2026-07-18-project-syn-top5000-sparse.tsv"
OUT_LEN4_TSV = ROOT / "docs" / "research" / "2026-07-18-project-syn-len4-top5000-sparse.tsv"
TOP_K = 5000
SPARSE_LT = 2
LEN4_CAMPAIGN_K = 5000


def undirected(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def load_lexicon(db_path: Path) -> set[str]:
    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT DISTINCT char FROM words").fetchall()
    con.close()
    out: set[str] = set()
    for (raw,) in rows:
        lit = normalize_literal(raw) if raw else None
        if lit:
            out.add(lit)
    return out


def load_db_syn_adj(db_path: Path, lex: set[str]) -> dict[str, set[str]]:
    con = sqlite3.connect(db_path)
    rows = con.execute(
        """
        SELECT a.char, b.char
        FROM word_relations r
        JOIN words a ON a.id = r.word_id
        JOIN words b ON b.id = r.related_id
        WHERE r.relation_type = 'syn'
        """
    ).fetchall()
    con.close()
    adj: dict[str, set[str]] = defaultdict(set)
    for raw_a, raw_b in rows:
        a = normalize_literal(raw_a) if raw_a else None
        b = normalize_literal(raw_b) if raw_b else None
        if not a or not b or a == b:
            continue
        if a not in lex or b not in lex:
            continue
        adj[a].add(b)
        adj[b].add(a)
    return adj


def merge_static_syn(adj: dict[str, set[str]], lex: set[str]) -> tuple[int, int]:
    """Add cilin＋guotong syns (both ends ∈ lex). Returns (cilin_edge_adds, guotong_edge_adds)."""
    cilin_adds = 0
    guotong_adds = 0
    load_cilin_index(str(ROOT / "data" / "cilin" / "new_cilin.txt"))
    load_thesaurus_dicts(
        syn_path=str(ROOT / "data" / "thesaurus" / "dict_synonym.txt"),
        ant_path=str(ROOT / "data" / "thesaurus" / "dict_antonym.txt"),
    )
    # Only probe heads that appear in static indexes ∩ lex
    for head in list(lex):
        for src, getter in (("cilin", get_cilin_synonyms), ("guotong", get_guotong_synonyms)):
            for raw in getter(head) or []:
                tail = normalize_literal(raw)
                if not tail or tail == head or tail not in lex:
                    continue
                if tail not in adj[head]:
                    adj[head].add(tail)
                    adj[tail].add(head)
                    if src == "cilin":
                        cilin_adds += 1
                    else:
                        guotong_adds += 1
    # each undirected edge counted twice above when both ends probed — report half-ish via unique pairs
    return cilin_adds, guotong_adds


def essay_top_in_lex(lex: set[str], k: int) -> list[tuple[str, int]]:
    """Essay freq DESC, literal ASC; only ∈ lex ∩ valid."""
    scored: list[tuple[str, int]] = []
    for lit in lex:
        if not is_valid_term(lit):
            continue
        scored.append((lit, int(get_essay_frequency(lit))))
    scored.sort(key=lambda t: (-t[1], t[0]))
    return scored[:k]


def hist_counts(counts: list[int]) -> dict[str, int]:
    c = Counter()
    for n in counts:
        if n <= 0:
            c["0"] += 1
        elif n == 1:
            c["1"] += 1
        elif n == 2:
            c["2"] += 1
        elif n <= 5:
            c["3-5"] += 1
        elif n <= 10:
            c["6-10"] += 1
        else:
            c["11+"] += 1
    return dict(sorted(c.items(), key=lambda kv: kv[0]))


def write_heads_tsv(path: Path, rows: list[tuple[int, str, int, int]]) -> None:
    """rank, head, essay_frequency, direct_syn_tails"""
    lines = ["rank\thead\tessay_frequency\tdirect_syn_tails"]
    for rank, head, freq, tails in rows:
        lines.append(f"{rank}\t{head}\t{freq}\t{tails}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_md(report: dict) -> str:
    t = report["top5000"]
    l4 = report["len4"]
    return f"""# 專案自建近義：直連近義過稀基線量度

**日期**：2026-07-18  
**契約**：`CONTEXT.md` — **直連近義過稀**＝尾數 ＜{SPARSE_LT}；常用＝Essay Top-{TOP_K} ∩ 過稀；成語＝len=4 proxy ∩ 過稀後再 Essay Top-{LEN4_CAMPAIGN_K}；兩母體去重（高頻優先）  
**可重跑**：`python scripts/research/project_syn_sparse_measure.py`  
**產物**：[`{OUT_JSON.name}`](./{OUT_JSON.name})、稀疏頭 TSV

## 結論摘要

| 母體 | 宇宙／候選 | 過稀或 freeze 規模 | 尾＝0 | 尾＝1 |
|------|------------|-------------------|-------|-------|
| Essay Top-{TOP_K} | {t['universe']} | **{t['sparse']}** 過稀（{t['sparse_pct']}%） | {t['sparse_zero']} | {t['sparse_one']} |
| len=4 全詞庫過稀 | {l4['universe']} 字面 | **{l4['sparse_raw']}** 過稀（去重後 {l4['sparse_deduped']}） | {l4['sparse_zero']} | {l4['sparse_one']} |
| **四字 campaign 擬 freeze** | 去重後過稀按 Essay 截斷 | **{l4['campaign_k']}** | {l4['campaign_zero']} | {l4['campaign_one']} |

**裁決**：高頻 campaign 母體 ≈ **{t['sparse']}** 頭（可開戰）。全庫 len4 過稀 ≈ **{l4['sparse_deduped']}** ≫ 5000 → **四字缺直連近義 campaign** 只 freeze Essay Top-{LEN4_CAMPAIGN_K}（已寫入 `CONTEXT.md`），唔一次清算。

## 直連近義定義（本量度）

無向鄰接＝`word_relations` syn（兩端 ∈ 詞庫字面）∪ cilin syn ∪ guotong syn（兩端 ∈ 詞庫；字面經 `normalize_literal`）。  
尾數＝該頭唯一鄰居數。

## Top-{TOP_K} 直連尾數分布

`{json.dumps(t['tail_hist'], ensure_ascii=False)}`

## 推進建議（對齊 grill）

1. 本報告＝量度閘；**尚未**正式 `campaign-freeze`。
2. 下一步：統一 CLI／資料夾骨架＋ **高頻近義 campaign**（終局含 `adequate_existing`）。
3. 高頻收官後再 freeze 四字 Top-{LEN4_CAMPAIGN_K}。
"""


def self_check(report: dict) -> None:
    t = report["top5000"]
    l4 = report["len4"]
    assert t["universe"] == TOP_K, t["universe"]
    assert t["sparse"] == t["sparse_zero"] + t["sparse_one"], t
    assert 0 <= t["sparse"] <= TOP_K
    assert l4["sparse_deduped"] <= l4["sparse_raw"]
    assert l4["campaign_k"] == min(LEN4_CAMPAIGN_K, l4["sparse_deduped"])
    assert l4["campaign_k"] == l4["campaign_zero"] + l4["campaign_one"]
    top_set = {h for _, h, _, _ in report["_top_rows"]}
    for _, h, _, _ in report["_len4_rows"]:
        assert h not in top_set, h
    for _, _, _, tails in report["_top_rows"]:
        assert tails < SPARSE_LT
    for _, _, _, tails in report["_len4_rows"]:
        assert tails < SPARSE_LT
    print("self-check OK")


def main() -> int:
    if not DB.is_file():
        raise SystemExit(f"missing DB: {DB}")
    load_essay_corpus()
    lex = load_lexicon(DB)
    adj = load_db_syn_adj(DB, lex)
    db_only_edges = sum(len(v) for v in adj.values()) // 2
    cilin_adds, guotong_adds = merge_static_syn(adj, lex)
    # unique undirected after merge
    seen_pairs: set[tuple[str, str]] = set()
    for a, tails in adj.items():
        for b in tails:
            seen_pairs.add(undirected(a, b))

    top = essay_top_in_lex(lex, TOP_K)
    top_counts = [len(adj.get(h, ())) for h, _ in top]
    top_sparse_rows: list[tuple[int, str, int, int]] = []
    rank = 0
    for head, freq in top:
        n = len(adj.get(head, ()))
        if n < SPARSE_LT:
            rank += 1
            top_sparse_rows.append((rank, head, freq, n))

    len4_universe = sorted(
        (h for h in lex if len(h) == 4 and is_valid_term(h)),
        key=lambda h: (-int(get_essay_frequency(h)), h),
    )
    top_sparse_set = {h for _, h, _, _ in top_sparse_rows}
    len4_sparse_raw_rows: list[tuple[str, int, int]] = []
    len4_deduped_rows: list[tuple[int, str, int, int]] = []
    z0 = z1 = 0
    for head in len4_universe:
        n = len(adj.get(head, ()))
        if n >= SPARSE_LT:
            continue
        freq = int(get_essay_frequency(head))
        len4_sparse_raw_rows.append((head, freq, n))
        if n == 0:
            z0 += 1
        else:
            z1 += 1
        if head in top_sparse_set:
            continue
        i = len(len4_deduped_rows) + 1
        len4_deduped_rows.append((i, head, freq, n))

    len4_campaign_rows = len4_deduped_rows[:LEN4_CAMPAIGN_K]

    report = {
        "contract": {
            "sparse_lt": SPARSE_LT,
            "top_k": TOP_K,
            "len4_campaign_k": LEN4_CAMPAIGN_K,
            "direct_syn": "word_relations.syn ∪ cilin ∪ guotong; both ends in lexicon",
        },
        "lexicon_literals": len(lex),
        "undirected_syn_pairs": len(seen_pairs),
        "db_syn_pairs_approx": db_only_edges,
        "static_neighbor_add_events": {
            "cilin": cilin_adds,
            "guotong": guotong_adds,
            "note": "directed add events while merging; not unique undirected edges",
        },
        "top5000": {
            "universe": len(top),
            "tail_hist": hist_counts(top_counts),
            "sparse": len(top_sparse_rows),
            "sparse_pct": round(100.0 * len(top_sparse_rows) / max(len(top), 1), 2),
            "sparse_zero": sum(1 for row in top_sparse_rows if row[3] == 0),
            "sparse_one": sum(1 for row in top_sparse_rows if row[3] == 1),
        },
        "len4": {
            "universe": len(len4_universe),
            "sparse_raw": len(len4_sparse_raw_rows),
            "sparse_zero": z0,
            "sparse_one": z1,
            "sparse_deduped": len(len4_deduped_rows),
            "overlap_with_top5000_sparse": len(len4_sparse_raw_rows) - len(len4_deduped_rows),
            "campaign_k": len(len4_campaign_rows),
            "campaign_zero": sum(1 for row in len4_campaign_rows if row[3] == 0),
            "campaign_one": sum(1 for row in len4_campaign_rows if row[3] == 1),
        },
        "_top_rows": top_sparse_rows,
        "_len4_rows": len4_campaign_rows,
    }

    self_check(report)

    public = {k: v for k, v in report.items() if not k.startswith("_")}
    OUT_JSON.write_text(
        json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    OUT_MD.write_text(render_md(report), encoding="utf-8")
    write_heads_tsv(OUT_TOP_TSV, top_sparse_rows)
    write_heads_tsv(OUT_LEN4_TSV, len4_campaign_rows)
    print(json.dumps(public, ensure_ascii=False, indent=2))
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")
    print(f"wrote {OUT_TOP_TSV} ({len(top_sparse_rows)} rows)")
    print(f"wrote {OUT_LEN4_TSV} ({len(len4_campaign_rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
