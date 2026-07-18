"""Measure daimaruhk/Cantonese.md term/answer membership vs lyrics.db."""
from __future__ import annotations

import io
import json
import re
import sqlite3
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import is_valid_term, normalize_literal  # noqa: E402

ARCHIVE = "https://codeload.github.com/daimaruhk/Cantonese.md/zip/refs/heads/main"
FM_RE = re.compile(r"^---\s*\n(.*?)\n---", re.S)
KV_RE = re.compile(
    r"^(term|termJyutping|answer|answerJyutping):\s*(.*)$", re.M
)


def norm_jp(s: str) -> str:
    return re.sub(r"\s+", "", s.strip().lower()) if s else ""


def main() -> None:
    req = urllib.request.Request(ARCHIVE, headers={"User-Agent": "Canto-0243-research"})
    print("downloading archive...")
    with urllib.request.urlopen(req, timeout=120) as r:
        blob = r.read()
    print("bytes", len(blob))
    zf = zipfile.ZipFile(io.BytesIO(blob))
    md_names = [
        n
        for n in zf.namelist()
        if "/src/contents/" in n.replace("\\", "/") and n.endswith(".md")
    ]
    print("md files", len(md_names))

    rows: list[dict[str, str]] = []
    for name in md_names:
        text = zf.read(name).decode("utf-8")
        m = FM_RE.search(text)
        if not m:
            continue
        d: dict[str, str] = {}
        for k, v in KV_RE.findall(m.group(1)):
            d[k] = v.strip().strip("\"'")
        if "term" in d:
            rows.append(d)
    print("parsed", len(rows))

    con = sqlite3.connect(ROOT / "lyrics.db")
    literals = {r[0] for r in con.execute("select distinct char from words")}
    readings: set[tuple[str, str]] = set()
    for ch, jp in con.execute("select char, jyutping from words"):
        if jp:
            readings.add((ch, norm_jp(jp)))
    print("db literals", len(literals), "readings", len(readings))

    def check_side(lit: str, jp: str) -> str:
        n = normalize_literal(lit) or lit
        if not n or not is_valid_term(n):
            return "invalid"
        if n not in literals:
            return "missing_literal"
        njp = norm_jp(jp)
        if njp and (n, njp) not in readings:
            return "missing_reading"
        return "ok"

    stats: Counter[str] = Counter()
    missing_lit: list[tuple[str, str, str]] = []
    missing_read: list[tuple[str, str, str]] = []
    invalid: list[tuple[str, str, str]] = []

    uniq: set[str] = set()
    for r in rows:
        for side, jpk in (("term", "termJyutping"), ("answer", "answerJyutping")):
            lit = r.get(side, "")
            jp = r.get(jpk, "")
            n = normalize_literal(lit) or lit
            if n:
                uniq.add(n)
            st = check_side(lit, jp)
            stats[st] += 1
            if st == "missing_literal":
                missing_lit.append((n, jp, side))
            elif st == "missing_reading":
                missing_read.append((n, jp, side))
            elif st == "invalid":
                invalid.append((n, jp, side))

    miss_uniq = sorted(uniq - literals)
    in_db = sorted(uniq & literals)
    miss_ok = [x for x in miss_uniq if 1 <= len(x) <= 12]
    miss_long = [x for x in miss_uniq if len(x) > 12]

    print("--- unique literals ---")
    print("union", len(uniq), "in_db", len(in_db), "missing", len(miss_uniq))
    print("missing len1-12", len(miss_ok), "len>12", len(miss_long))
    print("--- sides (term+answer) ---")
    for k, v in stats.most_common():
        print(k, v)
    print("missing_literal examples:")
    for t in missing_lit[:40]:
        print(" ", t)
    print("missing_reading", len(missing_read), missing_read[:12])
    print("invalid", invalid[:8])
    print("missing_ok sample", miss_ok[:60])

    out = {
        "source": "daimaruhk/Cantonese.md main zip",
        "n_md": len(rows),
        "uniq_union": len(uniq),
        "in_db": len(in_db),
        "missing_literal_uniq": len(miss_uniq),
        "missing_len_1_12": len(miss_ok),
        "missing_len_gt12": len(miss_long),
        "missing_rate_union": round(len(miss_uniq) / len(uniq), 4) if uniq else 0,
        "side_ok": stats["ok"],
        "side_missing_literal": stats["missing_literal"],
        "side_missing_reading": stats["missing_reading"],
        "side_invalid": stats["invalid"],
        "missing_literals_len_1_12": miss_ok,
        "missing_literals_long": miss_long,
        "missing_reading_samples": [
            {"char": a, "jyutping": b, "side": c} for a, b, c in missing_read[:50]
        ],
    }
    out_path = ROOT / "docs/research/2026-07-18-cantonese-md-membership.json"
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote", out_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
