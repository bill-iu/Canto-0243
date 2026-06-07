import json

def get_0243_code(jyutping: str) -> str:
    """根據 jyutping 產生 0243 code"""
    if not jyutping:
        return ""
    
    TONE_MAP = {1: "3", 2: "9", 3: "4", 4: "0", 5: "4", 6: "2"}
    
    syllables = jyutping.strip().split()
    code_parts = []
    
    for syl in syllables:
        if syl and syl[-1].isdigit():
            tone = int(syl[-1])
            code_parts.append(TONE_MAP.get(tone, "?"))
        else:
            code_parts.append("?")
    
    return "".join(code_parts)


from jyutping_table import JYUTPING_TABLE, SPECIAL_CASES

def split_jyutping(jyutping: str):
    """將 jyutping 拆分成 initials, finals, tones 三個 list"""
    if not jyutping or not isinstance(jyutping, str):
        return "[]", "[]", "[]"
    
    syllables = jyutping.strip().split()
    initials_list = []
    finals_list = []
    tones_list = []
    
    for syl in syllables:
        # 提取聲調
        tone = None
        final_start = len(syl)
        for k in range(len(syl)-1, -1, -1):
            if syl[k].isdigit():
                tone = int(syl[k])
                final_start = k
                break
        
        syllable = syl[:final_start]
        
        # 特殊處理 m / ng
        if syllable == "m":
            initials_list.append("m")
            finals_list.append("")
            tones_list.append(tone)
            continue
        if syllable == "ng":
            initials_list.append("ng")
            finals_list.append("")
            tones_list.append(tone)
            continue
        
        # 普通規則：找第一個元音
        vowels = 'aeiou'
        split_pos = -1
        for pos, char in enumerate(syllable):
            if char in vowels:
                split_pos = pos
                break
        
        initial = syllable[:split_pos] if split_pos != -1 else syllable
        final = syllable[split_pos:] if split_pos != -1 else ""
        
        initials_list.append(initial)
        finals_list.append(final)
        tones_list.append(tone)
    
    return json.dumps(initials_list), json.dumps(finals_list), json.dumps(tones_list)


def get_code_variants(code: str, mode: str = "m2") -> list:
    """生成 m1 / m2 的 code 等價變體"""
    if not code or not code.isdigit():
        return [code]
    
    variants = {code}
    
    if mode == "m1":
        mapping = {'5': '4', '4': '5', '6': '2', '2': '6', '9': '3', '3': '9'}
        
        # 單一替換
        current = code
        for old, new in mapping.items():
            if old in current:
                variants.add(current.replace(old, new))
        
        # 逐位替換（生成更多組合）
        for i in range(len(code)):
            for old, new in mapping.items():
                if code[i] == old:
                    new_code = code[:i] + new + code[i+1:]
                    variants.add(new_code)
    
    return sorted(list(variants))