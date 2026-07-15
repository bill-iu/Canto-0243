from pathlib import Path

t = Path("scripts/_len4_b03_land.py").read_text(encoding="utf-8")
t = t.replace("len4-b03-20260715", "len4-b04-20260715")
t = t.replace("len4_b03", "len4_b04")
t = t.replace("len4-b03", "len4-b04")
t = t.replace("SAMPLE_SEED = 20260718", "SAMPLE_SEED = 20260719")
t = t.replace("seed=20260718", "seed=20260719")
t = t.replace('"batch_index": 3', '"batch_index": 4')
old = """SAMPLE_FAILS = [
    ("付之東流", "落袋"),
    ("飄飄欲仙", "沮喪"),
]"""
new = """SAMPLE_FAILS = [
    ("口服心服", "口服心不服"),
    ("金雞獨立", "四平八穩"),
]"""
if old not in t:
    raise SystemExit("fails block missing")
t = t.replace(old, new)
Path("scripts/_len4_b04_land.py").write_text(t, encoding="utf-8")
print("ok")
