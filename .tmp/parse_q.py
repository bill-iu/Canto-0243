import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["READINESS_GATE_ENFORCE"] = "0"

from app.lexicon.rime_char_index import reset_rime_char_for_tests, load_rime_char_csv
from app.services.query_parse import normalize_and_parse
from app.services.query_match_spec_registry import build_match_spec_for_parsed

for csv in [None, ROOT / "data/rime/char.csv", ROOT / "data/rime/fixtures/char_sample.csv"]:
    reset_rime_char_for_tests()
    if csv:
        load_rime_char_csv(csv)
    p = normalize_and_parse("34=我")
    spec = build_match_spec_for_parsed(p) if p else None
    print("csv", csv and csv.name, "kind", getattr(p, "kind", type(p)), "spec", spec is not None)

for label, path in [("sample", ROOT / "data/rime/fixtures/char_sample.csv"), ("full", ROOT / "data/rime/char.csv")]:
    reset_rime_char_for_tests()
    load_rime_char_csv(path)
    p = normalize_and_parse("?yut?")
    spec = build_match_spec_for_parsed(p) if p else None
    print(label, "?yut?", getattr(p, "kind", type(p)), spec is not None)