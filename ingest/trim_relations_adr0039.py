"""
Offline trim word_relations for ADR-0039:
- GC1: group_codes JSON hierarchy → leaf code only
- S1 CAP-U@20: undirected syn neighbor cap
Then VACUUM.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

from app.domain.relations.cilin_codes import is_cilin_leaf_code
from app.domain.relations.degree_cap import SYN_NEIGHBOR_CAP, cap_undirected_syn_tuples


def _to_leaf(raw: object) -> str | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        if s[0] == "[":
            try:
                arr = json.loads(s)
                if isinstance(arr, list) and arr:
                    leaf = str(arr[-1])
                    return leaf if is_cilin_leaf_code(leaf) else leaf
            except (json.JSONDecodeError, TypeError):
                return s
            return None
        return s
    return None


def trim_db(db_path: Path | str, *, k: int = SYN_NEIGHBOR_CAP, vacuum: bool = True) -> dict:
    path = Path(db_path)
    stats = {"gc_updated": 0, "syn_before": 0, "syn_after": 0, "deleted": 0}

    with sqlite3.connect(path) as conn:
        # GC1
        rows = conn.execute(
            "SELECT rowid, group_codes FROM word_relations WHERE group_codes IS NOT NULL AND group_codes != ''"
        ).fetchall()
        for rowid, gc in rows:
            leaf = _to_leaf(gc)
            if leaf is None:
                continue
            if gc == leaf:
                continue
            # only rewrite if was JSON or longer hierarchy form
            if isinstance(gc, str) and (gc.strip().startswith("[") or gc != leaf):
                conn.execute(
                    "UPDATE word_relations SET group_codes = ? WHERE rowid = ?",
                    (leaf, rowid),
                )
                stats["gc_updated"] += 1

        # S1 load all
        all_rows = conn.execute(
            """
            SELECT word_id, related_id, relation_type, score, source, group_codes, id
            FROM word_relations
            """
        ).fetchall()
        syn_ids = []
        tuples = []
        id_by_key = {}
        for w, r, rtype, score, src, gc, rid in all_rows:
            t = (w, r, rtype, score, src, gc)
            tuples.append(t)
            if rtype == "syn":
                stats["syn_before"] += 1
                id_by_key[(w, r, rtype)] = rid
                syn_ids.append(rid)

        capped = cap_undirected_syn_tuples(tuples, k=k)
        keep_keys = {(t[0], t[1], t[2]) for t in capped if t[2] == "syn"}
        stats["syn_after"] = len(keep_keys)
        to_delete = [
            rid
            for (w, r, rt), rid in id_by_key.items()
            if (w, r, rt) not in keep_keys
        ]
        stats["deleted"] = len(to_delete)
        # batch delete
        for i in range(0, len(to_delete), 2000):
            chunk = to_delete[i : i + 2000]
            conn.executemany("DELETE FROM word_relations WHERE id = ?", [(x,) for x in chunk])
        conn.commit()
        if vacuum:
            conn.execute("VACUUM")

    return stats


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: python -m ingest.trim_relations_adr0039 <lyrics.db> [--no-vacuum]")
        return 2
    path = Path(args[0])
    vacuum = "--no-vacuum" not in args
    if not path.is_file():
        print(f"missing {path}")
        return 1
    st = trim_db(path, vacuum=vacuum)
    print(f"OK ADR-0039 trim {path}: {st}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
