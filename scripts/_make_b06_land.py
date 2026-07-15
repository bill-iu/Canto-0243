from pathlib import Path

t = Path("scripts/_len4_b05_land.py").read_text(encoding="utf-8")
t = t.replace("len4-b05-20260715", "len4-b06-20260715")
t = t.replace("len4_b05", "len4_b06")
t = t.replace("len4-b05", "len4-b06")
t = t.replace("SAMPLE_SEED = 20260720", "SAMPLE_SEED = 20260721")
t = t.replace("seed=20260720", "seed=20260721")
t = t.replace('"batch_index": 5', '"batch_index": 6')
old = """SAMPLE_FAILS = [
    ("不稂不莠", "優秀"),
    ("含垢忍辱", "不忍"),
    ("平地風波", "無事生非"),
    ("有史以來", "未來"),
    ("泰山鴻毛", "並重"),
]"""
new = """SAMPLE_FAILS = [
    ("小試牛刀", "全力以赴"),
    ("萬裏長城", "薄弱"),
]"""
if old not in t:
    raise SystemExit("fails block missing")
t = t.replace(old, new)
Path("scripts/_len4_b06_land.py").write_text(t, encoding="utf-8")
print("ok")
