import requests
import json
import time
import os
from tqdm import tqdm
from itertools import product

# ==================== 配置 ====================
API_URL = "https://www.0243.hk/api/cls/"
OUTPUT_FILE = "0243_dict_1to5digits.json"
DELAY = 0.6           # 可再調低至 0.5，如果被封再調高
TIMEOUT = 10
MAX_RETRIES = 2

digits = ['0', '2', '4', '9', '3']

# 生成 1~5 位所有排列
all_combinations = []
for length in range(1, 6):
    for combo in product(digits, repeat=length):
        all_combinations.append(''.join(combo))

print(f"總共 {len(all_combinations)} 個組合需要查詢...")

# ==================== 捉取函數 ====================
def fetch_for_num(num_str):
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(
                API_URL,
                json={"nums": num_str},
                timeout=TIMEOUT,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, list) and len(data) > 0:
                        return data
                except:
                    pass
            return []
        except:
            if attempt == MAX_RETRIES - 1:
                return []
            time.sleep(DELAY)
    return []

# ==================== 開始捉取 ====================
result_dict = {}
skipped = 0

print("開始捉取（已優化：自動跳過無數據組合）...\n")

for num in tqdm(all_combinations):
    words = fetch_for_num(num)
    if words:
        result_dict[num] = words
    else:
        skipped += 1
    time.sleep(DELAY)

# ==================== 儲存 ====================
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump({
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_requests": len(all_combinations),
        "successful_keys": len(result_dict),
        "skipped_empty": skipped,
        "data": result_dict
    }, f, ensure_ascii=False, indent=2)

print(f"\n✅ 捉取完成！")
print(f"   成功儲存 {len(result_dict)} 個有數據的組合")
print(f"   跳過 {skipped} 個無數據組合")
print(f"   檔案：{OUTPUT_FILE}  ({os.path.getsize(OUTPUT_FILE)/(1024*1024):.2f} MB)")