import json
from typing import List, Tuple

TONE_MAP = {1: "3", 2: "9", 3: "4", 4: "0", 5: "4", 6: "2"}
VOWELS = "aeiou"
M1_MAPPING = {"5": "4", "4": "5", "6": "2", "2": "6", "9": "3", "3": "9"}


def get_0243_code(jyutping: str) -> str:
    """根據 jyutping 產生 0243 code（逐音節聲調 → TONE_MAP digit，非韻母鍵盤）。"""
    if not jyutping:
        return ""

    syllables = jyutping.strip().split()
    return "".join(TONE_MAP.get(int(syl[-1]), "?") if syl and syl[-1].isdigit() else "?" for syl in syllables)


def split_jyutping(jyutping: str) -> Tuple[str, str, str]:
    """將 jyutping 拆分成 initials, finals, tones 三個 list"""
    if not isinstance(jyutping, str) or not jyutping.strip():
        return "[]", "[]", "[]"

    initials_list: List[str] = []
    finals_list: List[str] = []
    tones_list: List[int] = []

    for syllable_text in jyutping.strip().split():
        tone = None
        syllable = syllable_text
        for index in range(len(syllable_text) - 1, -1, -1):
            if syllable_text[index].isdigit():
                tone = int(syllable_text[index])
                syllable = syllable_text[:index]
                break

        if syllable in {"m", "ng"}:
            initials_list.append(syllable)
            finals_list.append("")
            tones_list.append(tone)
            continue

        split_pos = next((pos for pos, char in enumerate(syllable) if char in VOWELS), -1)
        initial = syllable[:split_pos] if split_pos != -1 else syllable
        final = syllable[split_pos:] if split_pos != -1 else ""

        # j- + y- nucleus: medial y belongs to final (yut, yu, yun), not initial cluster "jy"
        if initial == "jy" and final:
            initial = "j"
            final = "y" + final

        initials_list.append(initial)
        finals_list.append(final)
        tones_list.append(tone)

    return json.dumps(initials_list), json.dumps(finals_list), json.dumps(tones_list)


def rhyme_finals_from_jyutping(jyutping: str) -> list[str]:
    """韻母 list for rhyme compare; uses split_jyutping (jy- nucleus rules)."""
    if not jyutping or not str(jyutping).strip():
        return []
    _, finals_json, _ = split_jyutping(jyutping)
    try:
        parsed = json.loads(finals_json)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def get_code_variants(code: str, mode: str = "m2") -> List[str]:
    """生成 m1 / m2 的 code 等價變體"""
    if not code or not code.isdigit():
        return [code]

    variants = {code}

    if mode == "m1":
        for old, new in M1_MAPPING.items():
            if old in code:
                variants.add(code.replace(old, new))

        for index, digit in enumerate(code):
            if digit in M1_MAPPING:
                variants.add(code[:index] + M1_MAPPING[digit] + code[index + 1 :])

    return sorted(variants)
