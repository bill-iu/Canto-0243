from pathlib import Path

t = Path("scripts/_len4_b01_land.py").read_text(encoding="utf-8")
t = t.replace("len4-b01-20260715", "len4-b02-20260715")
t = t.replace("len4_b01", "len4_b02")
t = t.replace("len4-b01", "len4-b02")
t = t.replace("SAMPLE_SEED = 20260716", "SAMPLE_SEED = 20260717")
t = t.replace("seed=20260716", "seed=20260717")
t = t.replace('"batch_index": 1', '"batch_index": 2')
old = """SAMPLE_FAILS = [
    ("欲哭無淚", "喜極而泣"),
    ("無所不在", "罕見"),
    ("諸如此類", "與眾不同"),
]"""
new = """SAMPLE_FAILS = [
    ("千山萬水", "咫尺天涯"),
    ("有生以來", "從未"),
    ("潸然淚下", "破涕為笑"),
    ("紅男綠女", "清一色"),
]"""
if old not in t:
    raise SystemExit("SAMPLE_FAILS block not found")
t = t.replace(old, new)
Path("scripts/_len4_b02_land.py").write_text(t, encoding="utf-8")
print("ok", "千山萬水" in t)
