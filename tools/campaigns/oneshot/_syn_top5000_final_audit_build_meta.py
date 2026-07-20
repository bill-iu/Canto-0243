"""Build syn_top5000 final-audit meta from stratified samples + maintainer verdicts.

Does NOT mutate project_synonyms.tsv / ledgers. Removal is pending maintainer confirm
(see docs/research/2026-07-18-syn-top5000-final-audit.md).

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_top5000_final_audit_build_meta.py
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util  # noqa: E402

from tools.campaigns.project_antonyms_campaign import stratified_sample_no_natural  # noqa: E402
from tools.campaigns.project_synonyms_campaign import TOP5000_SYN_SPEC  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_syn_top5000_final_audit_sample",
    ROOT / "scripts" / "_syn_top5000_final_audit_sample.py",
)
_sample = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_sample)

ADEQ_OUT = _sample.ADEQ_OUT
ACC_OUT = _sample.ACC_OUT
BATCH_PREFIX = _sample.BATCH_PREFIX
NN_OUT = _sample.NN_OUT
SEED = _sample.SEED
NN_TSV = _sample.NN_TSV
ADEQ_TSV = _sample.ADEQ_TSV
_load_accepted = _sample._load_accepted
_load_manifest = _sample._load_manifest
_sha256 = _sample._sha256
stratified_sample_accepted_by_head = _sample.stratified_sample_accepted_by_head
stratified_sample_adequate = _sample.stratified_sample_adequate

OUT_META = (
    ROOT / "data" / "syn_ant" / "project" / "campaign_syn_top5000_final_audit.meta.json"
)

# Accepted fails: (head, tail) as in sample TSV (directed as landed).
FAIL_ACCEPTED: Dict[Tuple[str, str], str] = {
    ("你好", "問好"): "招呼語 vs 動詞「問好」，唔可獨立替換",
    ("呻吟", "哼"): "程度／窄化，唔係同義層近義",
    ("師兄", "師弟"): "輩分對立，非近義",
    ("打機", "遊戲"): "動詞 vs 名詞，詞性／論元唔同",
    ("熊仔", "熊"): "上下位（細稱→類名）",
    ("狗仔", "犬"): "上下位；且「狗仔」可指狗仔隊",
    ("相機", "攝影機"): "相關器材，非可替換近義",
    ("社會", "世上"): "相關域，非同義層",
    ("車站", "火車站"): "上下位（泛稱→火車專稱）",
    ("音樂", "歌曲"): "上下位／相關（音樂≠一首歌）",
    ("嘴角", "口角"): "「口角」常指爭執，替換唔穩定",
    ("大小姐", "小姐"): "程度／上下位",
    ("接住", "接著"): "異義（接住≠接著）",
    ("校車", "公車"): "相關／上下位（校車≠公車）",
    ("西瓜", "瓜"): "上下位",
    ("貓仔", "貓"): "上下位",
    ("鴨仔", "鴨"): "上下位",
    ("版主", "樓主"): "論壇角色不同，非近義",
    ("發票", "收據"): "相關單據，非近義",
    ("身高", "高度"): "相關量度，人高≠泛高度",
    ("銅", "黃銅"): "金屬種類不同／上下位",
    ("世紀", "時代"): "相關時間單位，非近義",
    ("男神", "偶像"): "相關／窄化（男神≠泛偶像）",
    ("神父", "牧師"): "宗教職銜不同",
    ("立法", "制定"): "相關／上下位（立法≠泛制定）",
    ("客服", "服務員"): "職銜近似，非近義",
    ("正所謂", "所謂"): "「所謂」常貶義，唔等同「正所謂」",
    ("陰道", "產道"): "相關解剖，填詞唔可穩定替換",
    ("輸入法", "打字法"): "相關技術，非近義",
    ("高中", "中學"): "上下位（高中⊂中學）",
}

# no_natural fails: head → reason
FAIL_NN: Dict[str, str] = {
    "下次": "有明顯自然近義「下回」，應改判 accepted",
    "會話": "有明顯自然近義「對話」，應改判 accepted",
    "好少": "有明顯自然近義「很少」，應改判 accepted",
    "踢波": "有明顯自然近義「踢球」，應改判 accepted",
    "無人": "有明顯自然近義「沒人」，應改判 accepted",
    "點講": "有明顯自然近義「怎麼說」，應改判 accepted",
    "夜貓": "有明顯自然近義「夜貓子」，應改判 accepted",
    "握手": "reason=function_word 唔貼（實義動詞）",
    "考研": "reason=function_word 唔貼",
    "荃灣": "reason 應為 proper_name_or_deixis",
    "設計師": "reason=function_word 唔貼",
    "陰毛": "reason=function_word 唔貼",
    "冷汗": "reason=function_word 唔貼",
    "情人節": "reason=function_word 唔貼（節日專名）",
    "九龍": "reason 應為 proper_name_or_deixis",
    "淘寶": "reason 應為 proper_name_or_deixis",
    "柯南": "reason 應為 proper_name_or_deixis",
    "話費": "reason=function_word 唔貼",
    "車型": "reason=function_word 唔貼",
    "麻甩佬": "reason=function_word 唔貼",
    "做愛": "reason=function_word 唔貼",
    "射出": "reason=function_word 唔貼",
    "嬴": "reason=function_word 唔貼",
    "搖搖板": "reason=function_word 唔貼",
    "關我事": "reason 宜 other_documented，非 function_word",
}

FAIL_ADEQ: Dict[str, str] = {
    "欄目": "現有直連「節目」屬欄目／節目相關，非填詞可用近義，不應裁 adequate",
}


def _git_head() -> str:
    return (
        subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True)
        .strip()
        .lower()
    )


def main() -> None:
    head_batch, campaign = _load_manifest()
    batch_count = max(head_batch.values())

    acc_rows = _load_accepted(campaign)
    acc = stratified_sample_accepted_by_head(
        acc_rows, seed=SEED, batch_count=batch_count
    )

    nn_all: List[Tuple[str, str, str]] = []
    with NN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not str(r.get("batch_id", "")).startswith(BATCH_PREFIX):
                continue
            h = r["head"].strip()
            if h in campaign:
                nn_all.append((h, r["reason"].strip(), r["batch_id"].strip()))
    nn = stratified_sample_no_natural(
        nn_all, head_batch, seed=SEED, batch_count=batch_count
    )

    adeq_all: List[Tuple[str, str, str]] = []
    with ADEQ_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not str(r.get("batch_id", "")).startswith(BATCH_PREFIX):
                continue
            h = r["head"].strip()
            if h in campaign:
                adeq_all.append((h, r["note"].strip(), r["batch_id"].strip()))
    adeq = stratified_sample_adequate(
        adeq_all, head_batch, seed=SEED, batch_count=batch_count
    )

    # Replay fixture files must match live sample
    with ACC_OUT.open(encoding="utf-8") as f:
        fixture_acc = [(r["head"], r["tail"]) for r in csv.DictReader(f, delimiter="\t")]
    assert fixture_acc == list(acc["sampled"]), "accepted sample drift; re-run sample script"

    acc_verdicts = []
    acc_removed_pending = []
    for h, t in acc["sampled"]:
        reason = FAIL_ACCEPTED.get((h, t))
        if reason:
            acc_verdicts.append(
                {"head": h, "tail": t, "verdict": "fail", "reasons": [reason]}
            )
            acc_removed_pending.append({"head": h, "tail": t, "reasons": [reason]})
        else:
            acc_verdicts.append({"head": h, "tail": t, "verdict": "ok", "reasons": []})
    acc_ok = sum(1 for v in acc_verdicts if v["verdict"] == "ok")
    acc_n = len(acc_verdicts)
    acc_rate = acc_ok / acc_n if acc_n else 0.0

    nn_verdicts = []
    nn_pending = []
    for h, r, _b in nn["sampled"]:
        reason = FAIL_NN.get(h)
        if reason:
            nn_verdicts.append(
                {"head": h, "reason": r, "verdict": "fail", "notes": reason}
            )
            nn_pending.append({"head": h, "reason": r, "notes": reason})
        else:
            nn_verdicts.append(
                {"head": h, "reason": r, "verdict": "ok", "notes": ""}
            )
    nn_ok = sum(1 for v in nn_verdicts if v["verdict"] == "ok")
    nn_n = len(nn_verdicts)
    nn_rate = nn_ok / nn_n if nn_n else 0.0

    adeq_verdicts = []
    adeq_pending = []
    for h, note, _b in adeq["sampled"]:
        reason = FAIL_ADEQ.get(h)
        if reason:
            adeq_verdicts.append(
                {"head": h, "note": note, "verdict": "fail", "notes": reason}
            )
            adeq_pending.append({"head": h, "note": note, "notes": reason})
        else:
            adeq_verdicts.append(
                {"head": h, "note": note, "verdict": "ok", "notes": ""}
            )
    adeq_ok = sum(1 for v in adeq_verdicts if v["verdict"] == "ok")
    adeq_n = len(adeq_verdicts)
    adeq_rate = adeq_ok / adeq_n if adeq_n else 0.0

    threshold = 0.9
    passed = acc_rate >= threshold and nn_rate >= threshold and adeq_rate >= threshold

    manifest_sha = _sha256(TOP5000_SYN_SPEC.manifest_tsv)
    audit = {
        "manifest_sha256": manifest_sha,
        "ok_rate_threshold": threshold,
        "git_commit": _git_head(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": "syn_top5000",
        "note": (
            f"syn_top5000 formal final audit seed={SEED}; "
            f"Acc {acc_ok}/{acc_n} (ok_rate={acc_rate:.4f}); "
            f"Nn {nn_ok}/{nn_n} (ok_rate={nn_rate:.4f}); "
            f"Adequate {adeq_ok}/{adeq_n} (ok_rate={adeq_rate:.4f}); "
            f"{'PASSED' if passed else 'FAILED'} gate≥{threshold}; "
            f"TSV/ledgers NOT mutated — "
            f"{len(acc_removed_pending)} accepted + {len(nn_pending)} nn + "
            f"{len(adeq_pending)} adequate fails pending maintainer apply"
        ),
        "accepted": {
            "status": acc["status"],
            "sample_seed": acc["sample_seed"],
            "sample_n": acc_n,
            "sample_ok": acc_ok,
            "sample_parent_n": acc["sample_parent_n"],
            "strata": acc["strata"],
            "sample_verdicts": acc_verdicts,
            # ponytail: empty until maintainer runs apply; fails still in sample_verdicts
            "removed_sample_fails": [],
            "pending_removal": acc_removed_pending,
        },
        "no_natural": {
            "status": nn["status"],
            "sample_seed": nn["sample_seed"],
            "sample_n": nn_n,
            "sample_ok": nn_ok,
            "sample_parent_n": nn["sample_parent_n"],
            "strata": nn["strata"],
            "sample_verdicts": nn_verdicts,
            "removed_sample_fails": [],
            "pending_rejudge": nn_pending,
        },
        "adequate_existing": {
            "status": adeq["status"],
            "sample_seed": adeq["sample_seed"],
            "sample_n": adeq_n,
            "sample_ok": adeq_ok,
            "sample_parent_n": adeq["sample_parent_n"],
            "strata": adeq["strata"],
            "sample_verdicts": adeq_verdicts,
            "removed_sample_fails": [],
            "pending_rejudge": adeq_pending,
        },
    }
    OUT_META.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {OUT_META.relative_to(ROOT)}")
    print(
        json.dumps(
            {
                "accepted": {"n": acc_n, "ok": acc_ok, "rate": round(acc_rate, 4)},
                "no_natural": {"n": nn_n, "ok": nn_ok, "rate": round(nn_rate, 4)},
                "adequate": {"n": adeq_n, "ok": adeq_ok, "rate": round(adeq_rate, 4)},
                "passed": passed,
                "fixture_acc": str(ACC_OUT.relative_to(ROOT)),
                "fixture_nn": str(NN_OUT.relative_to(ROOT)),
                "fixture_adeq": str(ADEQ_OUT.relative_to(ROOT)),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
