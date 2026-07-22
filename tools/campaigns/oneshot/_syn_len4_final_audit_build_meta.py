"""Build syn_len4 final-audit meta from stratified samples + maintainer verdicts.

Reaudit (seed=20260719) after first-audit apply. Historical first-audit
sample/verdicts remain in campaign_syn_len4_final_audit.meta.json under
`first_audit` when this script is run with --reaudit (default).

Does NOT mutate project_synonyms.tsv / ledgers. Removal is pending maintainer
confirm (see docs/research/2026-07-18-syn-len4-final-audit.md).

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_build_meta.py
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
from tools.campaigns.project_synonyms_campaign import LEN4_SYN_SPEC  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_syn_len4_final_audit_sample",
    ROOT / "scripts" / "_syn_len4_final_audit_sample.py",
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
_load_accepted_pairs = _sample._load_accepted_pairs
_load_adeq_rows = _sample._load_adeq_rows
_load_manifest = _sample._load_manifest
_load_nn_rows = _sample._load_nn_rows
_load_terminals = _sample._load_terminals
_sha256 = _sample._sha256
stratified_sample_accepted_by_head = _sample.stratified_sample_accepted_by_head
stratified_sample_adequate = _sample.stratified_sample_adequate

OUT_META = (
    ROOT / "data" / "syn_ant" / "project" / "campaign_syn_len4_final_audit.meta.json"
)

# --- reaudit (seed=20260719) fails ---
FAIL_ACCEPTED: Dict[Tuple[str, str], str] = {
    ("關鍵問題", "基礎問題"): "關鍵≠基礎，相關非近義",
    ("人仔細細", "小心翼翼"): "仔細形貌／態度≠小心翼翼動作，非可穩定替換",
    ("健健康康", "健康"): "重疊詞≠基形，上下位／冗餘",
    ("家庭教師", "補習老師"): "家教≠補習班老師，職銜／場景唔同",
    ("和平共處", "長期共存"): "和平共處≠長期共存",
    ("無處可逃", "無處可尋"): "逃≠尋",
    ("逆流而上", "逆風而行"): "逆流≠逆風",
    ("邊遠地區", "邊緣地區"): "邊遠≠邊緣",
    ("數字通信", "數據通信"): "數字通信≠數據通信",
    ("立法機關", "議會"): "立法機關≠議會（體制／範圍唔同）",
    ("長途旅行", "長途跋涉"): "旅行≠跋涉",
    ("威風八面", "威風凜凜"): "八面≠凜凜，氣勢相關非近義",
    ("牛肉拉麪", "牛肉麵"): "上下位（拉麵⊂麵）",
    ("交通擁擠", "擁擠不堪"): "擁擠狀態≠擁擠不堪（程度）",
    ("刻苦努力", "刻苦耐勞"): "努力≠耐勞",
    ("經濟落後", "貧窮落後"): "經濟落後≠貧窮落後",
    ("高等植物", "維管束植物"): "技術分類近義但唔可穩定替換",
    ("不成氣候", "不成器"): "不成氣候≠不成器",
    ("事隔多年", "事過境遷"): "隔年≠境遷",
    ("雷雨交加", "風雨交加"): "雷雨≠風雨",
    ("入境簽證", "簽證"): "上下位（入境簽證⊂簽證）",
    ("歡聲雷動", "掌聲雷動"): "歡聲≠掌聲",
    ("骨科醫生", "骨科"): "醫生≠科室",
    ("值得品味", "耐人尋味"): "品味（感官）≠耐人尋味（意蘊）",
    ("初級小學", "小學"): "上下位（初級小學⊂小學）",
    ("地緣戰略", "地緣政治"): "戰略≠政治",
    ("放手去做", "放手一搏"): "去做≠一搏",
    ("金融槓桿", "槓桿"): "上下位／省略（金融槓桿⊂槓桿）",
    ("丟盔卸甲", "抱頭鼠竄"): "潰敗丟盔≠抱頭鼠竄（場景唔同）",
    ("剖腹自殺", "剖腹"): "上下位／不完整",
    ("逆風而行", "逆流而上"): "逆風≠逆流",
    ("遠隔重洋", "遠渡重洋"): "遠隔≠遠渡",
    ("催眠狀態", "催眠"): "狀態≠過程／手段，上下位",
    ("頭腦清楚", "清醒"): "清楚≠清醒（意識層）",
}

FAIL_NN: Dict[str, str] = {
    "無藥可救": "有明顯自然近義「不可救藥」，應改判 accepted",
    "倒背如流": "有明顯自然近義「滾瓜爛熟」，應改判 accepted",
    "自相殘殺": "有明顯自然近義「同類相殘」，應改判 accepted",
    "反覆思量": "有明顯自然近義「思前想後」，應改判 accepted",
    "體外受精": "有明顯自然近義「試管受孕」，應改判 accepted",
}

FAIL_ADEQ: Dict[str, str] = {
    "喃喃自語": "覆蓋邊「喃喃」不完整／上下位，非填詞可用近義",
    "一線生機": "覆蓋邊「一線希望」生機≠希望，相關非近義",
    "直呼其名": "覆蓋邊「指名道姓」直呼≠指名道姓，語用不穩",
    "籠絡人心": "覆蓋邊「收買人心」籠絡≠收買，手段唔同",
}

# nn→accepted flips for apply (membership-checked offline)
NN_TO_ACCEPTED = {
    "無藥可救": "不可救藥",
    "倒背如流": "滾瓜爛熟",
    "自相殘殺": "同類相殘",
    "反覆思量": "思前想後",
    "體外受精": "試管受孕",
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

    acc_heads, _nn_heads, _adeq_heads, cover = _load_terminals(campaign)
    acc_rows = _load_accepted_pairs(campaign, acc_heads, head_batch, cover)
    acc = stratified_sample_accepted_by_head(
        acc_rows, seed=SEED, batch_count=batch_count
    )

    nn_all = _load_nn_rows(campaign)
    nn = stratified_sample_no_natural(
        nn_all, head_batch, seed=SEED, batch_count=batch_count
    )

    adeq_all = _load_adeq_rows(campaign)
    adeq = stratified_sample_adequate(
        adeq_all, head_batch, seed=SEED, batch_count=batch_count
    )

    with ACC_OUT.open(encoding="utf-8") as f:
        fixture_acc = [(r["head"], r["tail"]) for r in csv.DictReader(f, delimiter="\t")]
    assert fixture_acc == list(acc["sampled"]), "accepted sample drift; re-run sample script"

    with NN_OUT.open(encoding="utf-8") as f:
        fixture_nn = [
            (r["head"], r["reason"], r["batch_id"])
            for r in csv.DictReader(f, delimiter="\t")
        ]
    assert fixture_nn == list(nn["sampled"]), "nn sample drift; re-run sample script"

    with ADEQ_OUT.open(encoding="utf-8") as f:
        fixture_adeq = [
            (r["head"], r["note"], r["batch_id"])
            for r in csv.DictReader(f, delimiter="\t")
        ]
    assert fixture_adeq == list(adeq["sampled"]), "adeq sample drift; re-run sample script"

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

    # Preserve first-audit snapshot if present
    first_audit = None
    if OUT_META.exists():
        prev = json.loads(OUT_META.read_text(encoding="utf-8"))
        if prev.get("first_audit"):
            first_audit = prev["first_audit"]
        elif prev.get("audit_round") != "reaudit":
            # Whole prior meta was the first formal audit (seed 20260718 + apply)
            first_audit = prev

    manifest_sha = _sha256(LEN4_SYN_SPEC.manifest_tsv)
    audit = {
        "manifest_sha256": manifest_sha,
        "ok_rate_threshold": threshold,
        "git_commit": _git_head(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "campaign_id": "syn_len4",
        "audit_round": "reaudit",
        "sample_seed": SEED,
        "note": (
            f"syn_len4 reaudit seed={SEED} (post first-audit apply); "
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
        "nn_to_accepted_plan": [
            {"head": h, "tail": t} for h, t in NN_TO_ACCEPTED.items()
        ],
        "gate_status": "PASSED" if passed else "FAILED",
    }
    if first_audit is not None:
        audit["first_audit"] = first_audit

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
