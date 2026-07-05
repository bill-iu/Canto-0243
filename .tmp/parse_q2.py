import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["READINESS_GATE_ENFORCE"] = "0"

from app.services.query_parse import normalize_and_parse
from app.services.query_match_spec_registry import build_match_spec_for_parsed

p = normalize_and_parse("?yut?")
print("kind", p.kind if p else None)
print("spec", build_match_spec_for_parsed(p))