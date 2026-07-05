import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["READINESS_GATE_ENFORCE"] = "0"

from app.lexicon.rime_char_index import reset_rime_char_for_tests, load_rime_char_csv
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import parse_query
from app.services.query_match_spec_registry import build_match_spec_for_parsed

reset_rime_char_for_tests()
load_rime_char_csv(ROOT / "data/rime/fixtures/char_sample.csv")
p = parse_query(normalize_search_query("?yut?"))
spec = build_match_spec_for_parsed(p)
print("kind", p.kind, "spec", spec is not None)