import json
from typing import FrozenSet, List, Optional, Set, Tuple

TONE_MAP = {1: "3", 2: "9", 3: "4", 4: "0", 5: "5", 6: "2"}
VOWELS = "aeiou"
M1_MAPPING = {"5": "4", "4": "5", "6": "2", "2": "6", "9": "3", "3": "9"}
M2_LOOSE_MAPPING = {"4": "5", "5": "4"}
# ponytail: CONTEXT § 02493 碼 — query-only digits → stored 394052 碼（函數名保留）
M02493_TO_0243 = {"1": "3", "5": "5", "6": "2", "7": "3", "8": "4"}
STANDALONE_NASAL_FINALS = frozenset({"m", "ng"})


def get_0243_code(jyutping: str) -> str:
    """根據 jyutping 產生 394052 碼（逐音節聲調 → TONE_MAP digit，非韻母鍵盤）。"""
    if not jyutping:
        return ""

    syllables = jyutping.strip().split()
    return "".join(TONE_MAP.get(int(syl[-1]), "?") if syl and syl[-1].isdigit() else "?" for syl in syllables)


def split_jyutping_parts(jyutping: str) -> Tuple[List[str], List[str], List[Optional[int]]]:
    """Jyutping → (initials, finals, tones) token lists (not storage encoding)."""
    if not isinstance(jyutping, str) or not jyutping.strip():
        return [], [], []

    initials_list: List[str] = []
    finals_list: List[str] = []
    tones_list: List[Optional[int]] = []

    for syllable_text in jyutping.strip().split():
        tone: Optional[int] = None
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

        # y- 韻核：辅音叢集 + y + 元音 → y… 歸韻母（zyu→z+yu；yau 的 y 係聲母故 split_pos<2）
        if split_pos >= 2 and syllable[split_pos - 1] == "y" and final:
            initial = syllable[: split_pos - 1]
            final = "y" + final

        initials_list.append(initial)
        finals_list.append(final)
        tones_list.append(tone)

    return initials_list, finals_list, tones_list


def split_jyutping(jyutping: str) -> Tuple[str, str, str]:
    """
    Jyutping → storage strings for initials/finals + tones JSON.
    ADR-0037: initials/finals are compact id strings (S1), not JSON arrays.
    """
    from app.domain.lexicon.phoneme_codec import encode_phoneme_list

    initials_list, finals_list, tones_list = split_jyutping_parts(jyutping)
    if not initials_list and not finals_list:
        return "", "", "[]"
    return (
        encode_phoneme_list(initials_list, "initial"),
        encode_phoneme_list(finals_list, "final"),
        json.dumps(tones_list),
    )


def rhyme_finals_from_jyutping(jyutping: str) -> list[str]:
    """韻母 list for rhyme compare; uses split_jyutping_parts (y- 韻核規則)."""
    if not jyutping or not str(jyutping).strip():
        return []
    _ini, finals_list, _tones = split_jyutping_parts(jyutping)
    return list(finals_list)

def normalize_02493_code(code: str) -> str:
    """02493 碼逐位正規化為詞庫 394052 碼（CONTEXT § 02493 碼）。"""
    if not code or not code.isdigit():
        return code
    return "".join(M02493_TO_0243.get(digit, digit) for digit in code)


def _loose_digit_options(digit: str, mapping: dict[str, str]) -> tuple[str, ...]:
    if digit in mapping:
        return tuple(sorted({digit, mapping[digit]}))
    return (digit,)


def _loose_mapping_for_mode(mode: str) -> dict[str, str] | None:
    if mode in ("m1", "0243"):
        return M1_MAPPING
    if mode in ("m2", "02493"):
        return M2_LOOSE_MAPPING
    return None


def get_code_variants(code: str, mode: str = "m2") -> List[str]:
    """生成 m1 / m2 / m3 的 code 等價變體（先 02493→394052 正規化，再按模式鬆檔）。"""
    if not code or not code.isdigit():
        return [code]

    code = normalize_02493_code(code)
    mapping = _loose_mapping_for_mode(mode)
    if mapping is None:
        return [code]

    from itertools import product

    return sorted({"".join(combo) for combo in product(*(_loose_digit_options(d, mapping) for d in code))})


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
        _ini, fins, _tones = split_jyutping_parts(token)
        final = str(fins[0]) if fins else ""
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
    assert set(get_code_variants("021", "m1")) == {"023", "029", "063", "069"}
    assert get_code_variants("021", "m2") == ["023"]
    assert set(get_code_variants("4", "m2")) == {"4", "5"}
    assert get_code_variants("45", "m3") == ["45"]
    assert "93" in get_code_variants("39", "m1")
    assert STANDALONE_NASAL_FINALS <= expand_standalone_nasal_final_options({"m"})
    assert rhyme_final_tuples_compatible("m4", "ng5")
    assert rhyme_final_key_sets_compatible(
        rhyme_final_index_keys_per_position("m4")[0],
        rhyme_final_index_keys_per_position("ng5")[0],
    )
    from app.domain.lexicon.phoneme_codec import decode_phoneme_field

    assert decode_phoneme_field(split_jyutping("zyu6")[1], "final") == ["yu"]
    assert decode_phoneme_field(split_jyutping("fu6")[1], "final") == ["u"]
    print("OK")
