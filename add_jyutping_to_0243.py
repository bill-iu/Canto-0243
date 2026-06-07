import json
from pathlib import Path
import pycantonese
from pyjyutping import jyutping
from utils import split_jyutping

input_file = Path("data/raw/0243_dict_1to5digits.json")
output_file = Path("data/raw/merged_0243_with_jyutping.json")

print("正在讀取 0243_dict_1to5digits.json...")

with open(input_file, "r", encoding="utf-8") as f:
    full_data = json.load(f)

data_section = full_data.get("data", {})

print(f"共有 {len(data_section)} 個 code 組")

result = []
seen = set()

print("開始為詞語添加 jyutping（pycantonese → pyjyutping fallback）...")

for code, words in data_section.items():
    for word in words:
        if not word:
            continue
            
        word = str(word).strip()
        key = (word, code)
        if key in seen:
            continue
        seen.add(key)
        
        jyutping_str = "?"
        
        # 優先使用 pycantonese
        try:
            jyutping_list = pycantonese.characters_to_jyutping(word)
            if jyutping_list:
                jyutping_str = " ".join([item[1] for item in jyutping_list])
        except Exception:
            pass
        
        # 如果 pycantonese 失敗或返回 "?"，改用 pyjyutping
        if jyutping_str == "?" or not jyutping_str:
            try:
                jyutping_str = jyutping.convert(word)
                if not jyutping_str:
                    jyutping_str = "?"
            except Exception:
                jyutping_str = "?"
        
        # 使用你的 utils 拆分
        initials, finals, tones = split_jyutping(jyutping_str)
        
        result.append({
            "char": word,
            "jyutping": jyutping_str,
            "code": code,
            "initials": initials,
            "finals": finals,
            "tones": tones
        })

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f"✅ 處理完成！共產生 {len(result)} 筆資料")
print(f"已儲存至: {output_file}")