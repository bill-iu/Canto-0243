from pathlib import Path

t = Path("scripts/_len4_b02_land.py").read_text(encoding="utf-8")
t = t.replace("len4-b02-20260715", "len4-b03-20260715")
t = t.replace("len4_b02", "len4_b03")
t = t.replace("len4-b02", "len4-b03")
t = t.replace("SAMPLE_SEED = 20260717", "SAMPLE_SEED = 20260718")
t = t.replace("seed=20260717", "seed=20260718")
t = t.replace('"batch_index": 2', '"batch_index": 3')
old = """SAMPLE_FAILS = [
    ("千山萬水", "咫尺天涯"),
    ("有生以來", "從未"),
    ("潸然淚下", "破涕為笑"),
    ("紅男綠女", "清一色"),
]"""
new = """SAMPLE_FAILS = [
    ("付之東流", "落袋"),
    ("飄飄欲仙", "沮喪"),
]"""
if old not in t:
    raise SystemExit("fails block missing")
t = t.replace(old, new)
Path("scripts/_len4_b03_land.py").write_text(t, encoding="utf-8")
print("ok")
