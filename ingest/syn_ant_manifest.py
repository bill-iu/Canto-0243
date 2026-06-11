from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data" / "syn_ant" / "sources.yaml"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required for sources.yaml. Install with: pip install pyyaml"
        ) from exc
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_manifest(path: Optional[str | Path] = None) -> List[Dict[str, Any]]:
    manifest_path = Path(path) if path else DEFAULT_MANIFEST
    if not manifest_path.exists():
        return []
    data = _load_yaml(manifest_path)
    sources = data.get("sources") or []
    out: List[Dict[str, Any]] = []
    for src in sources:
        if not isinstance(src, dict) or not src.get("id"):
            continue
        item = dict(src)
        item["id"] = str(item["id"])
        item["source_rank"] = int(item.get("source_rank") or 50)
        item["enabled_by_default"] = bool(item.get("enabled_by_default"))
        item["local_only"] = bool(item.get("local_only"))
        out.append(item)
    return out


def resolve_source_path(src: Dict[str, Any], key: str = "raw_path") -> Optional[Path]:
    rel = src.get(key) or src.get("paths", {}).get(key)
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        p = ROOT / p
    return p


def select_sources(
    manifest: List[Dict[str, Any]],
    source_ids: Optional[List[str]] = None,
    defaults_only: bool = False,
) -> List[Dict[str, Any]]:
    if source_ids:
        wanted = {s.strip() for s in source_ids if s.strip()}
        return [s for s in manifest if s["id"] in wanted]
    if defaults_only:
        return [s for s in manifest if s.get("enabled_by_default")]
    return list(manifest)


def source_availability(src: Dict[str, Any]) -> Dict[str, Any]:
    """Report whether a source's required files exist."""
    info = {"id": src["id"], "available": True, "missing": []}
    if src.get("parser") == "current_static":
        paths = src.get("paths") or {}
        for label, rel in paths.items():
            p = ROOT / rel if not Path(rel).is_absolute() else Path(rel)
            if not p.exists():
                info["available"] = False
                info["missing"].append(f"{label}:{p}")
        return info
    raw = resolve_source_path(src)
    if raw and not raw.exists():
        info["available"] = False
        info["missing"].append(str(raw))
    return info


def manifest_report(manifest: Optional[List[Dict[str, Any]]] = None) -> str:
    manifest = manifest or load_manifest()
    lines = ["Syn/Ant source manifest report", "=" * 40]
    for src in manifest:
        avail = source_availability(src)
        flag = "OK" if avail["available"] else "MISSING"
        lines.append(
            f"- {src['id']}: {flag} | default={src.get('enabled_by_default')} "
            f"| license={src.get('license')} | parser={src.get('parser')}"
        )
        for m in avail.get("missing") or []:
            lines.append(f"    missing: {m}")
    return "\n".join(lines)
