"""Re-label idiom_u_auto with real POS + family only for true idioms."""
from __future__ import annotations

import csv
from pathlib import Path

IN = Path(__file__).resolve().parent / "idiom_u_auto.tsv"
OUT = Path(__file__).resolve().parent / "idiom_u_relabel.tsv"

# Not idioms — POS only, family empty
NOT_IDIOM = {
    "吉爾吉斯": "n",  # place
    "學士學位": "n",
    "學校同學": "n",
    "同班同學": "n",
    "電子電路": "n",
    "當且僅當": "r,x",  # logical connective
    "我愛我家": "v",  # slogan / clause
}

# Explicit POS overrides (true idioms / set phrases)
OVERRIDE = {
    "一夫一妻": "n,a",
    "一房一廳": "n",
    "一手一足": "n",
    "一分一秒": "n,r",
    "一時一刻": "n,r",
    "一時三刻": "n,r",
    "一年一度": "a,r",
    "一點一滴": "n,r",
    "今生今世": "n,r",
    "何年何月": "n,r",
    "何時何地": "n,r",
    "全黨全軍": "n",
    "各行各業": "n",
    "各色各樣": "a,n",
    "天兵天將": "n",
    "徒子徒孫": "n",
    "民脂民膏": "n",
    "童男童女": "n",
    "老夫老妻": "n",
    "阿貓阿狗": "n",
    "新人新事": "n",
    "真人真事": "n",
    "真刀真槍": "n,a",
    "大是大非": "n",
    "大魚大肉": "n,a",
    "大吉大利": "a",
    "大富大貴": "a",
    "大紅大紫": "a",
    "大紅大綠": "a",
    "原汁原味": "a,n",
    "古色古香": "a",
    "成雙成對": "a,v",
    "成千成萬": "a,r",
    "寸土寸金": "a,n",
    "本鄉本土": "n,a",
    "獨門獨户": "a,n",
    "永生永世": "r",
    "年復一年": "r",
    "日復一日": "r",
    "先到先得": "v,r",
    "多勞多得": "v,a",
    "公事公辦": "v",
    "亦步亦趨": "v,a",
    "一清二白": "a",
    "一望無垠": "a",
    "一往無前": "a,v",
    "一心一意": "a,r",
    "一心二用": "v,a",
    "一事無成": "a,v",
    "一來一往": "v,r",
    "一來二去": "r,v",
    "自由自在": "a,r",
    "自暴自棄": "v,a",
    "至始至終": "r",  # often 自始至終
    "徹頭徹尾": "r,a",
    "畢恭畢敬": "a,r",
    "美輪美奐": "a",
    "如火如茶": "a,r",
    "如詩如畫": "a",
    "神乎其神": "a",
    "聞所未聞": "a",
    "痛定思痛": "v",
    "賊喊捉賊": "v",
    "話裏有話": "a,v",
    "難上加難": "a",
    "親上加親": "v,a",
    "天外有天": "a,n",
    "人無完人": "a,n",
    "仁者見仁": "v,a",
    "腳痛醫腳": "v",
    "愈演愈烈": "a,v",
    "愈戰愈勇": "a,v",
    "善有善報": "v,a",
    "惡有惡報": "v,a",
    "多子多福": "a,n",
    "大徹大悟": "v,a",
    "所作所為": "n",
    "所見所聞": "n",
    "學士學位": "n",
}


def default_pos(lit: str, pat: str) -> str:
    if lit in NOT_IDIOM:
        return NOT_IDIOM[lit]
    if lit in OVERRIDE:
        return OVERRIDE[lit]
    # ABAB: usually a,r or a
    if pat == "ABAB":
        return "a,r"
    # AxxA classic idioms → a,v default
    if pat == "AxxA":
        return "a,v"
    # ABAC: most are manner/state or action
    # 忽X忽Y / 時X時Y → r,a
    if lit.startswith("忽") or lit.startswith("時"):
        return "a,r"
    if lit.startswith("自") and len(lit) == 4:
        return "v,a"
    if lit.endswith("氣") or lit.endswith("腦"):
        return "a"  # 傻頭傻腦 / 好聲好氣
    if "來" in lit and "去" in lit:
        return "v,r"
    if lit.startswith("大") and len(lit) == 4:
        return "a,v"
    if lit.startswith("多") and len(lit) == 4:
        return "a"
    # default verbal/adjectival set phrase
    return "a,v"


def main() -> None:
    with IN.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    out = []
    for r in rows:
        lit = r["literal"].strip()
        pat = (r.get("pattern") or "").strip()
        pos = default_pos(lit, pat)
        family = "" if lit in NOT_IDIOM else "idiom"
        out.append({"literal": lit, "pattern": pat, "pos": pos, "family": family})
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=["literal", "pattern", "pos", "family"],
            delimiter="\t",
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} -> {OUT}")
    n_idiom = sum(1 for r in out if r["family"] == "idiom")
    print(f"family=idiom {n_idiom}; plain {len(out)-n_idiom}")


if __name__ == "__main__":
    main()
