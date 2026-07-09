#!/usr/bin/env python3
"""Codegen QueryKind meta from contracts/query-kind-manifest.json (ADR-0035).

Usage:
  python scripts/codegen_query_kind_manifest.py
  python scripts/codegen_query_kind_manifest.py --check
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "contracts" / "query-kind-manifest.json"
PY_OUT = REPO / "app" / "services" / "_generated" / "query_kind_registry.py"
TS_OUT = REPO / "client" / "src" / "db" / "_generated" / "query-kind-registry.ts"

ROUTE_ORDER = (
    "digit",
    "mask_family",
    "heteronym",
    "relation",
    "lookup",
    "unmatched",
    "empty",
)

HEADER_PY = '''\
"""AUTO-GENERATED from contracts/query-kind-manifest.json — do not edit.

Run: python scripts/codegen_query_kind_manifest.py
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

'''

HEADER_TS = '''\
/** AUTO-GENERATED from contracts/query-kind-manifest.json — do not edit.
 * Run: python scripts/codegen_query_kind_manifest.py
 */

'''


def _snake_to_member(kind_id: str) -> str:
    return kind_id.upper()


def load_manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    kinds = data.get("kinds")
    if not isinstance(kinds, dict) or not kinds:
        raise SystemExit("manifest.kinds must be a non-empty object")
    routes_used: set[str] = set()
    for kid, meta in kinds.items():
        if not isinstance(meta, dict):
            raise SystemExit(f"kind {kid!r}: meta must be object")
        route = meta.get("route")
        if route not in ROUTE_ORDER:
            raise SystemExit(f"kind {kid!r}: unknown route {route!r}")
        if "match_spec" not in meta or not isinstance(meta["match_spec"], bool):
            raise SystemExit(f"kind {kid!r}: match_spec must be bool")
        routes_used.add(route)
    return data


def render_py(kinds: dict) -> str:
    lines = [HEADER_PY]
    lines.append("class QueryKind(str, Enum):\n")
    lines.append('    """Parsed query classification (domain syntax types)."""\n\n')
    for kid in kinds:
        lines.append(f'    {_snake_to_member(kid)} = "{kid}"\n')
    lines.append("\n\nclass RouteKind(str, Enum):\n")
    for route in ROUTE_ORDER:
        lines.append(f'    {route.upper()} = "{route}"\n')
    lines.append(
        "\n\n@dataclass(frozen=True)\n"
        "class QueryKindMeta:\n"
        "    route: RouteKind\n"
        "    match_spec: bool = False\n\n\n"
        "QUERY_KIND_META: dict[QueryKind, QueryKindMeta] = {\n"
    )
    for kid, meta in kinds.items():
        member = f"QueryKind.{_snake_to_member(kid)}"
        route = f"RouteKind.{meta['route'].upper()}"
        if meta["match_spec"]:
            lines.append(f"    {member}: QueryKindMeta({route}, match_spec=True),\n")
        else:
            lines.append(f"    {member}: QueryKindMeta({route}),\n")
    lines.append("}\n\n")
    lines.append(
        "MASK_FAMILY_KINDS: frozenset[QueryKind] = frozenset(\n"
        "    k for k, m in QUERY_KIND_META.items() if m.route == RouteKind.MASK_FAMILY\n"
        ")\n"
        "MATCH_SPEC_KINDS: frozenset[QueryKind] = frozenset(\n"
        "    k for k, m in QUERY_KIND_META.items() if m.match_spec\n"
        ")\n\n\n"
        "def route_kind_for(kind: QueryKind) -> RouteKind:\n"
        "    meta = QUERY_KIND_META.get(kind)\n"
        "    if meta is None:\n"
        "        return RouteKind.EMPTY\n"
        "    return meta.route\n\n\n"
        "def uses_match_spec_kind(kind: QueryKind) -> bool:\n"
        "    meta = QUERY_KIND_META.get(kind)\n"
        "    if meta is None:\n"
        "        return False\n"
        "    return meta.match_spec\n\n\n"
        "__all__ = [\n"
        '    "MASK_FAMILY_KINDS",\n'
        '    "MATCH_SPEC_KINDS",\n'
        '    "QUERY_KIND_META",\n'
        '    "QueryKind",\n'
        '    "QueryKindMeta",\n'
        '    "RouteKind",\n'
        '    "route_kind_for",\n'
        '    "uses_match_spec_kind",\n'
        "]\n"
    )
    return "".join(lines)


def render_ts(kinds: dict) -> str:
    lines = [HEADER_TS]
    lines.append("export enum QueryKind {\n")
    for kid in kinds:
        lines.append(f"  {_snake_to_member(kid)} = '{kid}',\n")
    lines.append("}\n\nexport enum RouteKind {\n")
    for route in ROUTE_ORDER:
        lines.append(f"  {route.upper()} = '{route}',\n")
    lines.append(
        "}\n\nexport interface QueryKindMeta {\n"
        "  route: RouteKind;\n"
        "  match_spec?: boolean;\n"
        "}\n\nexport const QUERY_KIND_META: Record<QueryKind, QueryKindMeta> = {\n"
    )
    for kid, meta in kinds.items():
        member = f"QueryKind.{_snake_to_member(kid)}"
        route = f"RouteKind.{meta['route'].upper()}"
        if meta["match_spec"]:
            lines.append(f"  [{member}]: {{ route: {route}, match_spec: true }},\n")
        else:
            lines.append(f"  [{member}]: {{ route: {route} }},\n")
    lines.append(
        "};\n\n"
        "export const MASK_FAMILY_KINDS: ReadonlySet<QueryKind> = new Set(\n"
        "  Object.entries(QUERY_KIND_META)\n"
        "    .filter(([, meta]) => meta.route === RouteKind.MASK_FAMILY)\n"
        "    .map(([kind]) => kind as QueryKind),\n"
        ");\n\n"
        "export const MATCH_SPEC_KINDS: ReadonlySet<QueryKind> = new Set(\n"
        "  Object.entries(QUERY_KIND_META)\n"
        "    .filter(([, meta]) => Boolean(meta.match_spec))\n"
        "    .map(([kind]) => kind as QueryKind),\n"
        ");\n\n"
        "export function routeKindFor(kind: QueryKind): RouteKind {\n"
        "  return QUERY_KIND_META[kind]?.route ?? RouteKind.EMPTY;\n"
        "}\n\n"
        "export function usesMatchSpec(kind: QueryKind): boolean {\n"
        "  return MATCH_SPEC_KINDS.has(kind);\n"
        "}\n"
    )
    return "".join(lines)


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if generated files would change",
    )
    args = parser.parse_args(argv)
    data = load_manifest()
    kinds = data["kinds"]
    py = render_py(kinds)
    ts = render_ts(kinds)

    if args.check:
        ok = True
        for path, content in ((PY_OUT, py), (TS_OUT, ts)):
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"stale: {path.relative_to(REPO)}", file=sys.stderr)
                ok = False
        if not ok:
            print("run: python scripts/codegen_query_kind_manifest.py", file=sys.stderr)
            return 1
        print("query-kind codegen clean")
        return 0

    changed = []
    if write_if_changed(PY_OUT, py):
        changed.append(PY_OUT)
    if write_if_changed(TS_OUT, ts):
        changed.append(TS_OUT)
    for path in changed:
        print(f"wrote {path.relative_to(REPO)}")
    if not changed:
        print("already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
