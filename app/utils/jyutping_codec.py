import json
from typing import FrozenSet, List, Set, Tuple

TONE_MAP = {1: "3", 2: "9", 3: "4", 4: "0", 5: "4", 6: "2"}
VOWELS = "aeiou"
M1_MAPPING = {"5": "4", "4": "5", "6": "2", "2": "6", "9": "3", "3": "9"}
# ponytail: CONTEXT § 02493 碼 — query-only digits → stored 0243 碼
M02493_TO_0243 = {"1": "3", "5": "4", "6": "2", "7": "3", "8": "4"}
STANDALONE_NASAL_FINALS = frozenset({"m", "ng"})


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


def normalize_02493_code(code: str) -> str:
    """02493 碼逐位正規化為詞庫 0243 碼（CONTEXT § 02493 碼）。"""
    if not code or not code.isdigit():
        return code
    return "".join(M02493_TO_0243.get(digit, digit) for digit in code)


def get_code_variants(code: str, mode: str = "m2") -> List[str]:
    """生成 m1 / m2 的 code 等價變體（先 02493→0243 正規化，m1 再鬆檔展開）。"""
    if not code or not code.isdigit():
        return [code]

    code = normalize_02493_code(code)
    variants = {code}

    if mode == "m1":
        for old, new in M1_MAPPING.items():
            if old in code:
                variants.add(code.replace(old, new))

        for index, digit in enumerate(code):
            if digit in M1_MAPPING:
                variants.add(code[:index] + M1_MAPPING[digit] + code[index + 1 :])

    return sorted(variants)


def _syllable_letters(token: str) -> str:
    for index in range(len(token) - 1, -1, -1):
        if token[index].isdigit():
            return token[:index].lower()
    return token.lower()


def syllable_token_at(jyutping: str, pos: int) -> str:
    tokens = (jyutping or "").strip().split()
    if pos < 0 or pos >= len(tokens):
        return ""
    return tokens[pos]


def is_standalone_nasal_syllable_token(token: str) -> bool:
    """整節僅 m／ng（加調）— 領域上無聲母（CONTEXT § 獨立鼻音韻母）。"""
    return _syllable_letters(token or "") in STANDALONE_NASAL_FINALS


def expand_standalone_nasal_final_options(options: Set[str]) -> Set[str]:
    """m／ng 獨立韻母等價（mrpinyin M／NG 欄；CONTEXT § 韻母粵拼錨）。"""
    if options & STANDALONE_NASAL_FINALS:
        return set(options) | set(STANDALONE_NASAL_FINALS)
    if options == {""}:
        return set(options) | set(STANDALONE_NASAL_FINALS)
    return options


def rhyme_final_index_keys_per_position(jyutping: str) -> list[FrozenSet[str]]:
    """每音節韻母索引鍵；獨立 m／ng 音節同時帶 m 與 ng。"""
    keys: list[FrozenSet[str]] = []
    for token in (jyutping or "").strip().split():
        letters = _syllable_letters(token)
        if letters in STANDALONE_NASAL_FINALS:
            keys.append(STANDALONE_NASAL_FINALS)
            continue
        _, finals_json, _ = split_jyutping(token)
        try:
            arr = json.loads(finals_json)
        except (TypeError, json.JSONDecodeError):
            arr = []
        final = str(arr[0]) if arr else ""
        keys.append(frozenset({final}) if final else frozenset())
    return keys


def rhyme_final_key_sets_compatible(a: FrozenSet[str], b: FrozenSet[str]) -> bool:
    if not a and not b:
        return True
    if not a or not b:
        return False
    return bool(a & b)


def rhyme_final_tuples_compatible(jyutping_a: str, jyutping_b: str) -> bool:
    keys_a = rhyme_final_index_keys_per_position(jyutping_a)
    keys_b = rhyme_final_index_keys_per_position(jyutping_b)
    if len(keys_a) != len(keys_b):
        return False
    return all(rhyme_final_key_sets_compatible(x, y) for x, y in zip(keys_a, keys_b))


if __name__ == "__main__":
    assert normalize_02493_code("021") == "023"
    assert "023" in get_code_variants("021", "m1")
    assert get_code_variants("021", "m2") == ["023"]
    assert STANDALONE_NASAL_FINALS <= expand_standalone_nasal_final_options({"m"})
    assert rhyme_final_tuples_compatible("m4", "ng5")
    assert rhyme_final_key_sets_compatible(
        rhyme_final_index_keys_per_position("m4")[0],
        rhyme_final_index_keys_per_position("ng5")[0],
    )
    print("OK")
