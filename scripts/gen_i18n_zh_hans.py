"""Generate committed Simplified Chinese UI catalogs from Traditional sources."""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import opencc
except ImportError:
    raise SystemExit(
        "Missing opencc-python-reimplemented. Run: pip install -r requirements-dev.txt"
    )

CONVERTER = opencc.OpenCC("t2s")
SOURCE = REPO_ROOT / "shared" / "workbench-i18n.mjs"
OUTPUT = REPO_ROOT / "shared" / "generated" / "zh-hans.generated.mjs"
ZH_BLOCK = re.compile(r"\n  zh: \{\n(?P<body>.*?)\n  \},\n  zhHans:", re.DOTALL)
ENTRY = re.compile(r"^\s{4}(?P<key>[A-Za-z][A-Za-z0-9]*): (?P<value>'(?:\\.|[^'])*'),$")

# Product terminology that intentionally differs from raw OpenCC conversion.
OVERRIDES = {
    "正篩選候選": "正在筛选候选",
}


def read_traditional_catalog() -> dict[str, str]:
    source = SOURCE.read_text(encoding="utf-8")
    block = ZH_BLOCK.search(source)
    if not block:
        raise ValueError(f"Traditional catalog block not found in {SOURCE}")
    result: dict[str, str] = {}
    for line in block.group("body").splitlines():
        match = ENTRY.match(line)
        if not match:
            raise ValueError(f"Unsupported catalog entry: {line}")
        value = ast.literal_eval(match.group("value"))
        if not isinstance(value, str):
            raise ValueError(f"Catalog value is not text: {line}")
        result[match.group("key")] = value
    return result


def simplify(value: str) -> str:
    return OVERRIDES.get(value, CONVERTER.convert(value))


def render() -> str:
    entries = read_traditional_catalog()
    lines = [
        "// GENERATED FILE — DO NOT EDIT. Run: python scripts/gen_i18n_zh_hans.py --write",
        "export const GENERATED_ZH_HANS = Object.freeze({",
        "  workbench: Object.freeze({",
    ]
    for key, value in entries.items():
        escaped = simplify(value).replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"    {key}: '{escaped}',")
    lines.extend(["  }),", "});", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify committed Simplified Chinese catalogs."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify output (default)")
    mode.add_argument("--write", action="store_true", help="refresh generated output")
    args = parser.parse_args()

    expected = render()
    actual = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(expected, encoding="utf-8", newline="\n")
        print(f"Updated: {OUTPUT.relative_to(REPO_ROOT)}")
        return 0
    if actual != expected:
        print(
            "Generated Simplified Chinese catalog is stale; "
            "run `python scripts/gen_i18n_zh_hans.py --write`."
        )
        return 1
    print(f"OK: {OUTPUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
