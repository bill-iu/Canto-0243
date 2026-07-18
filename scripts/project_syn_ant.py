#!/usr/bin/env python3
"""專案自建近反義統一維護入口（近義／反義子命令）。

Examples:
  python scripts/project_syn_ant.py syn measure
  python scripts/project_syn_ant.py syn campaign-freeze --campaign syn_top5000
  python scripts/project_syn_ant.py syn campaign-freeze --campaign syn_len4 --force
  python scripts/project_syn_ant.py ant campaign-validate --campaign top5000
"""
from __future__ import annotations

import argparse
import json
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cmd_syn_measure(_args: argparse.Namespace) -> int:
    measure = ROOT / "scripts" / "research" / "project_syn_sparse_measure.py"
    runpy.run_path(str(measure), run_name="__main__")
    return 0


def cmd_syn_ensure_list(_args: argparse.Namespace) -> int:
    from ingest.project_synonyms import ensure_empty_list

    ensure_empty_list()
    print(json.dumps({"ok": True, "action": "ensure_empty_list"}, ensure_ascii=False))
    return 0


def cmd_syn_campaign_freeze(args: argparse.Namespace) -> int:
    from app.lexicon.essay_index import load_essay_corpus
    from ingest.project_synonyms import ensure_empty_list
    from ingest.project_synonyms_campaign import freeze_syn_campaign

    load_essay_corpus()
    ensure_empty_list()
    try:
        result = freeze_syn_campaign(
            campaign_id=args.campaign,
            db_path=args.db,
            force=bool(args.force),
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_ant_passthrough(args: argparse.Namespace) -> int:
    """Delegate remaining argv to scripts/project_antonyms.py."""
    import subprocess

    ant = ROOT / "scripts" / "project_antonyms.py"
    passthrough = list(args.ant_argv)
    if passthrough and passthrough[0] == "--":
        passthrough = passthrough[1:]
    return int(subprocess.call([sys.executable, str(ant), *passthrough]))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="專案自建近反義維護入口（syn／ant）",
    )
    sub = p.add_subparsers(dest="family", required=True)

    syn = sub.add_parser("syn", help="專案自建近義")
    syn_sub = syn.add_subparsers(dest="syn_cmd", required=True)

    p_m = syn_sub.add_parser("measure", help="過稀基線量度（research script）")
    p_m.set_defaults(func=cmd_syn_measure)

    p_e = syn_sub.add_parser("ensure-list", help="建立空近義清單＋meta")
    p_e.set_defaults(func=cmd_syn_ensure_list)

    p_f = syn_sub.add_parser("campaign-freeze", help="凍結近義 campaign manifest")
    p_f.add_argument(
        "--campaign",
        default="syn_top5000",
        choices=("syn_top5000", "syn_len4"),
    )
    p_f.add_argument(
        "--db",
        default=str(ROOT / "client" / "public" / "lyrics.db"),
    )
    p_f.add_argument(
        "--force",
        action="store_true",
        help="覆寫已有 manifest",
    )
    p_f.set_defaults(func=cmd_syn_campaign_freeze)

    def _land_batch(script_name: str):
        def _fn(_args: argparse.Namespace) -> int:
            runpy.run_path(str(ROOT / "scripts" / script_name), run_name="__main__")
            return 0

        return _fn

    p_b01 = syn_sub.add_parser(
        "land-b01",
        help="入帳 syn_top5000 batch-1",
    )
    p_b01.set_defaults(func=_land_batch("_syn_top5000_b01_land.py"))
    p_b02 = syn_sub.add_parser(
        "land-b02",
        help="入帳 syn_top5000 batch-2",
    )
    p_b02.set_defaults(func=_land_batch("_syn_top5000_b02_land.py"))
    p_b03 = syn_sub.add_parser(
        "land-b03",
        help="入帳 syn_top5000 batch-3",
    )
    p_b03.set_defaults(func=_land_batch("_syn_top5000_b03_land.py"))
    p_b04 = syn_sub.add_parser(
        "land-b04",
        help="入帳 syn_top5000 batch-4",
    )
    p_b04.set_defaults(func=_land_batch("_syn_top5000_b04_land.py"))
    p_b05 = syn_sub.add_parser(
        "land-b05",
        help="入帳 syn_top5000 batch-5",
    )
    p_b05.set_defaults(func=_land_batch("_syn_top5000_b05_land.py"))
    p_b06 = syn_sub.add_parser(
        "land-b06",
        help="入帳 syn_top5000 batch-6",
    )
    p_b06.set_defaults(func=_land_batch("_syn_top5000_b06_land.py"))
    p_l01 = syn_sub.add_parser(
        "land-len4-b01",
        help="入帳 syn_len4 batch-1",
    )
    p_l01.set_defaults(func=_land_batch("_syn_len4_b01_land.py"))
    p_l02 = syn_sub.add_parser(
        "land-len4-b02",
        help="入帳 syn_len4 batch-2",
    )
    p_l02.set_defaults(func=_land_batch("_syn_len4_b02_land.py"))
    p_l03 = syn_sub.add_parser(
        "land-len4-b03",
        help="入帳 syn_len4 batch-3",
    )
    p_l03.set_defaults(func=_land_batch("_syn_len4_b03_land.py"))
    p_l04 = syn_sub.add_parser(
        "land-len4-b04",
        help="入帳 syn_len4 batch-4",
    )
    p_l04.set_defaults(func=_land_batch("_syn_len4_b04_land.py"))
    p_l05 = syn_sub.add_parser(
        "land-len4-b05",
        help="入帳 syn_len4 batch-5",
    )
    p_l05.set_defaults(func=_land_batch("_syn_len4_b05_land.py"))
    p_l06 = syn_sub.add_parser(
        "land-len4-b06",
        help="入帳 syn_len4 batch-6",
    )
    p_l06.set_defaults(func=_land_batch("_syn_len4_b06_land.py"))
    p_l07 = syn_sub.add_parser(
        "land-len4-b07",
        help="入帳 syn_len4 batch-7",
    )
    p_l07.set_defaults(func=_land_batch("_syn_len4_b07_land.py"))
    p_l08 = syn_sub.add_parser(
        "land-len4-b08",
        help="入帳 syn_len4 batch-8",
    )
    p_l08.set_defaults(func=_land_batch("_syn_len4_b08_land.py"))
    p_l09 = syn_sub.add_parser(
        "land-len4-b09",
        help="入帳 syn_len4 batch-9",
    )
    p_l09.set_defaults(func=_land_batch("_syn_len4_b09_land.py"))
    p_l10 = syn_sub.add_parser(
        "land-len4-b10",
        help="入帳 syn_len4 batch-10",
    )
    p_l10.set_defaults(func=_land_batch("_syn_len4_b10_land.py"))

    ant = sub.add_parser(
        "ant",
        help="轉呼 scripts/project_antonyms.py（其餘參數原樣傳遞）",
    )
    ant.add_argument(
        "ant_argv",
        nargs=argparse.REMAINDER,
        help="project_antonyms.py 參數，如: campaign-validate --campaign top5000",
    )
    ant.set_defaults(func=cmd_ant_passthrough)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.family == "ant" and args.ant_argv and args.ant_argv[0] == "--":
        args.ant_argv = args.ant_argv[1:]
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
