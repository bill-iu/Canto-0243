from pathlib import Path

t = Path("scripts/_len4_b04_land.py").read_text(encoding="utf-8")
t = t.replace("len4-b04-20260715", "len4-b05-20260715")
t = t.replace("len4_b04", "len4_b05")
t = t.replace("len4-b04", "len4-b05")
t = t.replace("SAMPLE_SEED = 20260719", "SAMPLE_SEED = 20260720")
t = t.replace("seed=20260719", "seed=20260720")
t = t.replace('"batch_index": 4', '"batch_index": 5')
old = """SAMPLE_FAILS = [
    ("口服心服", "口服心不服"),
    ("金雞獨立", "四平八穩"),
]"""
new = """SAMPLE_FAILS = [
    ("不稂不莠", "優秀"),
    ("含垢忍辱", "不忍"),
    ("平地風波", "無事生非"),
    ("有史以來", "未來"),
    ("泰山鴻毛", "並重"),
]"""
if old not in t:
    raise SystemExit("fails block missing")
t = t.replace(old, new)
Path("scripts/_len4_b05_land.py").write_text(t, encoding="utf-8")
print("ok")
