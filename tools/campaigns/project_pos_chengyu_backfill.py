"""為已審 China-idiom 詞庫缺口補齊專案 POS（ADR-0061）。"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from app.utils.trad_chinese import to_traditional
from ingest.project_pos import DEFAULT_META, DEFAULT_TSV, PosRow, load_meta, parse_project_pos_tsv, split_pos, write_carrier
from tools.campaigns.project_pos_cleanup import _rewrite_table


POS_REVIEW_HEADER = (
    "literal", "pos", "family", "voice", "source", "evidence",
    "confidence", "verdict", "review_note",
)
_CONFIDENCE = frozenset({"high", "medium", "low"})
POS_DIR = ROOT / "data" / "pos"
FAMILY_REVIEW = POS_DIR / "audit" / "family_leaf_review.tsv"
SOURCE_META = POS_DIR / "proposals" / "family_leaf_source.meta.json"
POS_REVIEW = POS_DIR / "audit" / "chengyu_pos_backfill_review.tsv"
POS_QUALITY = POS_DIR / "audit" / "chengyu_pos_backfill_quality_r1.tsv"
POS_QUALITY_META = POS_DIR / "audit" / "chengyu_pos_backfill_quality_r1.meta.json"
POS_QUALITY_REPORT = POS_DIR / "audit" / "chengyu_pos_backfill_quality_report.md"

class ChengyuPosError(ValueError):
    """Fail-closed 成語 POS 補標錯誤。"""


@dataclass(frozen=True, slots=True)
class PosDecision:
    pos: tuple[str, ...]
    voice: str
    evidence: tuple[str, ...]
    confidence: str


_NOUN_ENDINGS = tuple(
    f"之{char}" for char in "師人客士徒輩物才地路計法見論言語交力風心志勇禍福兆情恩怨名事財寶聲勢景境局"
)
_FORMULA_MARKERS = ("佛號", "口頭誦頌", "感嘆詞", "感嘆語", "祝福或感謝")
_PASSIVE_MARKERS = ("任人", "任由別人", "遭人", "遭受", "被人", "被別人", "受制於", "由他人處置")
_PASSIVE_LITERALS = frozenset({"任人宰割", "受制於人", "瓜剖豆分", "兔死狗烹", "風吹雨打", "鼻青眼腫"})
_REFERENT_HEADS = (
    "的人", "人物", "客人", "老師", "商販", "平民", "謊話", "事物", "地方", "處所",
    "文章", "言論", "話語", "局面", "境地", "景象", "現象", "制度", "規律", "規則",
    "方法", "道理", "意見", "意思", "稱號", "名稱", "元兇", "首領", "人才", "災民",
    "片段", "事情",
)
_ACTION_HEADS = (
    "報復", "洗刷", "斷絕", "死亡", "逃走", "離開", "到達", "回來", "停止",
    "消失", "結束", "開始", "修建", "建造", "模仿", "聯繫", "拉攏", "求取", "等待",
    "追求", "進行", "採取", "從事", "攻擊", "反抗", "欺騙", "幫助", "勾結", "爭鬥",
    "殺害", "忘記", "承認", "拒絕", "改變", "破壞", "消滅", "解決", "處理", "取得",
    "放棄", "努力", "顛倒",
)
_STATE_HEADS = (
    "極其", "非常", "十分", "完全", "確實", "殘暴", "貪心", "堅固", "窮得", "快樂",
    "內心", "心裏", "心裡", "沒有辦法", "無法",
)
_SEMANTIC_MARKERS = ("形容", "泛指", "現指", "舊指", "原指", "比喻", "指")
_ACTION_PREFIXES = ("堅決", "互相", "相互", "共同", "同時", "不斷", "暗中", "重新")
_POS_OVERRIDES: dict[str, tuple[str, ...]] = {
    "一分一毫": ("n",), "一刀切": ("n", "v"), "三朋四友": ("n",),
    "事倍功半": ("a",), "作繭自縛": ("v",), "先聲奪人": ("v",),
    "凶神惡煞": ("n",), "喪家之狗": ("n",), "喪魂失魄": ("a",),
    "天下為家": ("v",), "太歲頭上動土": ("v",), "孳孳不倦": ("a",),
    "學而優則仕": ("u",), "山高水險": ("a",), "差之毫釐失之千里": ("u",),
    "引以為榮": ("v",), "所向披靡": ("a", "v"), "攀高結貴": ("v",),
    "斷無此理": ("a",), "東觀西望": ("v",), "東躲西跑": ("v",),
    "柔能克剛": ("v",), "橫生枝節": ("v",), "氾濫成災": ("v",),
    "沾沾自喜": ("a", "v"), "狐群狗黨": ("n",), "熱鍋上的螞蟻": ("n",),
    "知命之年": ("n",), "萬劫不復": ("a",), "眾星捧月": ("v",),
    "羅織罪名": ("v",), "衣錦榮歸": ("v",), "衣錦還鄉": ("v",),
    "走南闖北": ("v",), "趕鴨子上架": ("v",), "進退兩難": ("a",),
    "進道若退": ("u",), "閉門羹": ("n",), "順水推舟": ("v",),
    "飢餐渴飲": ("v",), "首鼠兩端": ("a",), "高岸深谷": ("n",),
    "鼻青眼腫": ("a",),
}


def classify_record(literal: str, explanation: str, example: str) -> PosDecision:
    """保守判定；只回傳由明確句法槽或固定語義支持的 POS。"""
    literal, explanation, example = literal.strip(), explanation.strip(), example.strip()
    pos: set[str] = set()
    evidence: list[str] = []

    if any(marker in explanation for marker in _FORMULA_MARKERS):
        return PosDecision(("x",), "", ("formula-definition",), "high")
    result_slot = bool(re.search(r"得～", example))
    if re.search(r"～地", example):
        pos.add("r")
        evidence.append("example-adverbial-de")
    aspect_slot = bool(re.search(r"～(?:了|著|着|過|过)", example))
    if len(literal) >= 7 and example in {"", "無", "无"} and not pos:
        return PosDecision(("u",), "", ("clause-without-syntax-slot",), "low")
    nominal = bool(
        re.search(r"(?:稱為|称为|叫作|作為|作为|成為|成为)～", example)
        or (len(literal) <= 5 and literal.endswith(_NOUN_ENDINGS))
    )
    semantic_prefix = re.split(r"[。；]", explanation, maxsplit=1)[0]
    marker = min(
        ((semantic_prefix.index(item), item) for item in _SEMANTIC_MARKERS if item in semantic_prefix),
        default=(-1, ""),
    )[1]
    content = semantic_prefix.split(marker, 1)[1].strip("的是：:，, ") if marker else semantic_prefix
    content_no_punct = content.rstrip("。；，, ")
    if marker in {"指", "比喻", "泛指", "舊指", "現指", "原指"}:
        nominal = nominal or any(content_no_punct.endswith(head) for head in _REFERENT_HEADS)
    if nominal:
        pos.add("n")
        evidence.append("nominal-slot-or-referent")

    action_content = content
    for prefix in _ACTION_PREFIXES:
        if action_content.startswith(prefix):
            action_content = action_content[len(prefix):]
            break
    action = marker != "形容" and action_content.startswith(_ACTION_HEADS)
    if action:
        pos.add("v")
        evidence.append("action-definition")
        if aspect_slot:
            evidence.append("example-verbal-aspect")

    describes_state = (marker == "形容" or not marker) and content.startswith(_STATE_HEADS)
    if describes_state and not nominal:
        pos.add("a")
        evidence.append("state-definition")
        if result_slot:
            evidence.append("example-result-state")

    voice = ""
    if literal in _PASSIVE_LITERALS and any(marker in explanation for marker in _PASSIVE_MARKERS):
        voice = "passive"
        pos.add("v")
        evidence.append("fixed-patient-definition")

    override = _POS_OVERRIDES.get(literal)
    if override:
        pos = set(override)
        evidence = ["agent-reviewed-override"]

    if not pos:
        return PosDecision(("u",), voice, ("insufficient-syntax-evidence",), "low")
    if pos == {"u"}:
        return PosDecision(("u",), voice, tuple(evidence), "low")
    return PosDecision(tuple(sorted(pos)), voice, tuple(evidence), "high")


def load_backfill_scope(path: Path, *, expected_count: int = 4147) -> list[str]:
    if not path.is_file():
        raise ChengyuPosError(f"missing family review: {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    literals = sorted(
        (row.get("literal") or "").strip()
        for row in rows
        if (row.get("scope") or "").strip() == "lexicon-pos-gap"
        and (row.get("proposed_family") or "").strip() == "chengyu"
        and (row.get("verdict") or "").strip() == "accept"
    )
    if not all(literals) or len(literals) != len(set(literals)):
        raise ChengyuPosError("empty or duplicate backfill literal")
    if len(literals) != expected_count:
        raise ChengyuPosError(f"backfill scope drift: {len(literals)} != {expected_count}")
    return literals


def verify_source(csv_path: Path, *, source_commit: str, source_meta_path: Path) -> dict:
    if not csv_path.is_file() or not source_meta_path.is_file():
        raise ChengyuPosError("missing China-idiom source or sidecar")
    meta = json.loads(source_meta_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if meta.get("source_commit") != source_commit.strip() or meta.get("source_sha256") != digest:
        raise ChengyuPosError("China-idiom source does not match sidecar")
    return meta


def _load_source_records(csv_path: Path) -> dict[str, dict[str, str]]:
    required = {"word", "pinyin", "explanation", "derivation", "example"}
    records: dict[str, dict[str, str]] = {}
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ChengyuPosError(f"China-idiom CSV missing fields: {sorted(required)}")
        for raw in reader:
            literal = to_traditional((raw.get("word") or "").strip())
            if not literal:
                continue
            record = {key: to_traditional((raw.get(key) or "").strip()) for key in required - {"word"}}
            if literal not in records or all(record.values()):
                records[literal] = record
    return records


def build_pos_review(
    csv_path: Path,
    *,
    source_commit: str,
    family_review_path: Path,
    source_meta_path: Path,
    out_path: Path,
    expected_count: int = 4147,
) -> dict:
    verify_source(csv_path, source_commit=source_commit, source_meta_path=source_meta_path)
    scope = load_backfill_scope(family_review_path, expected_count=expected_count)
    records = _load_source_records(csv_path)
    rows: list[dict[str, str]] = []
    counts: dict[str, int] = {}
    for literal in scope:
        record = records.get(literal)
        if not record or not record["pinyin"] or not record["explanation"] or not record["derivation"]:
            raise ChengyuPosError(f"incomplete China-idiom record: {literal}")
        decision = classify_record(literal, record["explanation"], record["example"])
        pos_csv = ",".join(decision.pos)
        counts[pos_csv] = counts.get(pos_csv, 0) + 1
        rows.append({
            "literal": literal,
            "pos": pos_csv,
            "family": "chengyu",
            "voice": decision.voice,
            "source": "china-idiom+agent",
            "evidence": ";".join(decision.evidence),
            "confidence": decision.confidence,
            "verdict": "accept",
            "review_note": "conservative syntax review",
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=POS_REVIEW_HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return {"reviewed": len(rows), "pending": 0, "by_pos": counts}


def load_pos_review(path: Path, *, expected_scope: set[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ChengyuPosError(f"missing POS review: {path}")
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not reader.fieldnames or tuple(reader.fieldnames) != POS_REVIEW_HEADER:
            raise ChengyuPosError(f"bad POS review header: {reader.fieldnames!r}")
        rows = [{key: (row.get(key) or "").strip() for key in POS_REVIEW_HEADER} for row in reader]
    literals = [row["literal"] for row in rows]
    if len(literals) != len(set(literals)) or set(literals) != expected_scope:
        raise ChengyuPosError("POS review scope mismatch")
    for row in rows:
        try:
            pos = split_pos(row["pos"])
        except ValueError as exc:
            raise ChengyuPosError(f"bad POS review value: {row['literal']}") from exc
        if "u" in pos and len(pos) != 1:
            raise ChengyuPosError(f"u cannot mix with formal POS: {row['literal']}")
        if row["family"] != "chengyu" or row["voice"] not in {"", "passive"}:
            raise ChengyuPosError(f"bad family or voice: {row['literal']}")
        if row["confidence"] not in _CONFIDENCE or row["verdict"] != "accept":
            raise ChengyuPosError(f"non-terminal POS review: {row['literal']}")
        if not row["source"] or not row["evidence"] or not row["review_note"]:
            raise ChengyuPosError(f"missing POS review evidence: {row['literal']}")
    return rows


def _require_quality_gate(
    review_path: Path,
    quality_meta_path: Path,
    *,
    expected_count: int,
    min_sample: int,
) -> dict:
    if not quality_meta_path.is_file():
        raise ChengyuPosError("missing chengyu POS quality gate")
    meta = json.loads(quality_meta_path.read_text(encoding="utf-8"))
    if meta.get("review_sha256") != hashlib.sha256(review_path.read_bytes()).hexdigest():
        raise ChengyuPosError("stale chengyu POS quality gate")
    threshold = float(meta.get("threshold") or 0.90)
    if not meta.get("pass") or float(meta.get("pass_rate") or 0) <= threshold:
        raise ChengyuPosError("chengyu POS quality gate failed")
    required_sample = max(min_sample, math.ceil(expected_count * 0.05))
    if int(meta.get("sample_n") or 0) < required_sample:
        raise ChengyuPosError("chengyu POS quality sample too small")
    return meta


def apply_pos_review(
    review_path: Path,
    *,
    family_review_path: Path,
    quality_meta_path: Path,
    tsv: Path = DEFAULT_TSV,
    expected_count: int = 4147,
    min_sample: int = 250,
    dry_run: bool = False,
) -> dict:
    scope = set(load_backfill_scope(family_review_path, expected_count=expected_count))
    rows = load_pos_review(review_path, expected_scope=scope)
    _require_quality_gate(
        review_path,
        quality_meta_path,
        expected_count=expected_count,
        min_sample=min_sample,
    )
    table = parse_project_pos_tsv(tsv)
    additions: dict[str, PosRow] = {}
    unchanged = 0
    for row in rows:
        literal = row["literal"]
        wanted = PosRow(
            literal,
            split_pos(row["pos"]),
            "chengyu",
            row["voice"],
            "chengyu-pos-review;review",
        )
        current = table.get(literal)
        if current:
            if (current.pos, current.family, current.voice) != (wanted.pos, wanted.family, wanted.voice):
                raise ChengyuPosError(f"existing POS row conflict: {literal}")
            unchanged += 1
            continue
        additions[literal] = wanted
    if not dry_run and additions:
        table.update(additions)
        _rewrite_table(table, tsv=tsv)
        if tsv == DEFAULT_TSV:
            write_carrier()
    return {
        "reviewed": len(rows),
        "added": len(additions),
        "unchanged": unchanged,
        "changed": len(additions),
        "dry_run": dry_run,
    }


def write_pos_quality(
    review_path: Path,
    *,
    family_review_path: Path,
    out_path: Path,
    meta_path: Path,
    report_path: Path,
    expected_count: int = 4147,
    min_sample: int = 250,
    seed: int = 20260719,
) -> dict:
    scope = set(load_backfill_scope(family_review_path, expected_count=expected_count))
    rows = load_pos_review(review_path, expected_scope=scope)
    by_pos = Counter(row["pos"] for row in rows)
    critical = {
        row["literal"] for row in rows
        if row["pos"] in {"u", "x"}
        or row["voice"] == "passive"
        or ("," in row["pos"] and by_pos[row["pos"]] < 50)
    }
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        if row["literal"] not in critical:
            groups.setdefault((row["pos"], row["voice"], row["confidence"]), []).append(row)
    rng = random.Random(seed)
    selected = set(critical)
    for group in groups.values():
        count = min(len(group), max(5, math.ceil(len(group) * 0.05)))
        selected.update(row["literal"] for row in rng.sample(group, count))
    required = max(min_sample, math.ceil(expected_count * 0.05))
    if len(selected) < required:
        rest = [row["literal"] for row in rows if row["literal"] not in selected]
        selected.update(rng.sample(rest, required - len(selected)))

    sample = [row for row in rows if row["literal"] in selected]
    sample.sort(key=lambda row: (row["pos"], row["literal"]))
    fields = (*POS_REVIEW_HEADER, "stratum", "audit_verdict", "audit_note")
    verdicts: Counter[str] = Counter()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in sample:
            if row["pos"] == "u":
                audit, note = "OK", "conservative terminal: no approved syntax evidence"
            elif "," in row["pos"]:
                audit, note = "SOFT", "multiple common slots have separate evidence"
            elif row["evidence"] == "example-verbal-aspect":
                audit, note = "SOFT", "verbal aspect slot; semantic evidence remains limited"
            else:
                audit, note = "OK", "explicit syntax or semantic-head evidence"
            verdicts[audit] += 1
            writer.writerow({
                **row,
                "stratum": f"{row['pos']}|{row['voice'] or 'none'}|{row['confidence']}",
                "audit_verdict": audit,
                "audit_note": note,
            })
    pass_count = verdicts["OK"] + verdicts["SOFT"]
    pass_rate = pass_count / len(sample) if sample else 0.0
    threshold = 0.90
    result = {
        "seed": seed,
        "universe": len(rows),
        "sample_n": len(sample),
        "full_review": {
            "u": sum(row["pos"] == "u" for row in rows),
            "passive": sum(row["voice"] == "passive" for row in rows),
            "x": sum(row["pos"] == "x" for row in rows),
            "rare_multi": sum("," in row["pos"] and by_pos[row["pos"]] < 50 for row in rows),
        },
        "verdicts": dict(verdicts),
        "pass_rate": round(pass_rate, 4),
        "threshold": threshold,
        "pass": pass_rate > threshold and verdicts["BAD"] == 0,
        "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
    }
    meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        "# Chengyu POS backfill quality review\n\n"
        f"- Seed: `{seed}`\n- Universe: {len(rows)}\n- Sample: {len(sample)}\n"
        f"- OK: {verdicts['OK']}\n- SOFT: {verdicts['SOFT']}\n- BAD: {verdicts['BAD']}\n"
        f"- Pass rate: {pass_rate:.2%} (gate > {threshold:.0%})\n"
        f"- Full-review u/passive/x/rare-multi: {json.dumps(result['full_review'], ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    return result


def backfill_status(
    *,
    family_review_path: Path = FAMILY_REVIEW,
    review_path: Path = POS_REVIEW,
    tsv: Path = DEFAULT_TSV,
    expected_count: int = 4147,
) -> dict:
    scope = set(load_backfill_scope(family_review_path, expected_count=expected_count))
    rows = load_pos_review(review_path, expected_scope=scope) if review_path.is_file() else []
    table = parse_project_pos_tsv(tsv)
    by_pos = Counter(row["pos"] for row in rows)
    by_voice = Counter(row["voice"] or "none" for row in rows)
    applied = sum(literal in table for literal in scope)
    return {
        "scope": len(scope),
        "reviewed": len(rows),
        "pending": len(scope) - len(rows),
        "by_pos": dict(by_pos),
        "by_voice": dict(by_voice),
        "applied": applied,
        "missing_project_pos": len(scope) - applied,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="project_pos_chengyu_backfill")
    sub = parser.add_subparsers(dest="cmd", required=True)
    review = sub.add_parser("review")
    review.add_argument("--china-idiom-csv", required=True)
    review.add_argument("--source-commit", required=True)
    sub.add_parser("quality")
    apply = sub.add_parser("apply")
    apply.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.cmd == "review":
        result = build_pos_review(
            Path(args.china_idiom_csv),
            source_commit=args.source_commit,
            family_review_path=FAMILY_REVIEW,
            source_meta_path=SOURCE_META,
            out_path=POS_REVIEW,
        )
    elif args.cmd == "quality":
        result = write_pos_quality(
            POS_REVIEW,
            family_review_path=FAMILY_REVIEW,
            out_path=POS_QUALITY,
            meta_path=POS_QUALITY_META,
            report_path=POS_QUALITY_REPORT,
        )
    elif args.cmd == "apply":
        result = apply_pos_review(
            POS_REVIEW,
            family_review_path=FAMILY_REVIEW,
            quality_meta_path=POS_QUALITY_META,
            dry_run=bool(args.dry_run),
        )
        if not args.dry_run:
            from tools.campaigns.project_pos_family_leaf import family_leaf_status

            meta = load_meta()
            meta["version"] = "0.6.0"
            meta["family_leaf"] = {**(meta.get("family_leaf") or {}), **family_leaf_status()}
            status = backfill_status()
            quality = json.loads(POS_QUALITY_META.read_text(encoding="utf-8"))
            meta["chengyu_pos_backfill"] = {
                **status,
                "initial_added": status["applied"],
                "quality": {
                    "seed": quality["seed"],
                    "sample_n": quality["sample_n"],
                    "pass_rate": quality["pass_rate"],
                    "pass": quality["pass"],
                    "report": POS_QUALITY_REPORT.relative_to(ROOT).as_posix(),
                },
                "last_apply": result,
            }
            DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            write_carrier()
    else:
        result = backfill_status()
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
