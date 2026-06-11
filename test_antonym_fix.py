#!/usr/bin/env python
import re
from utils import load_antonym_dict, load_thesaurus_dicts, _ant_dict, get_antonyms

print("=== Testing bidirectional antonym parsing for guotong pairs ===")
print("Reloading...")
load_antonym_dict()
load_thesaurus_dicts()
print("Loaded.")

# Discover real pairs from the file
found = False
with open("data/thesaurus/dict_antonym.txt", encoding="utf-8") as f:
    for line in f:
        if "—" in line or "–" in line or "——" in line:
            m = re.search(r"(\S+)[—–—]+(\S+)", line)
            if m:
                a, b = m.group(1), m.group(2)
                print(f"Found pair in data: {a} — {b}")
                ants_a = _ant_dict.get(a, [])
                ants_b = _ant_dict.get(b, [])
                has_b_for_a = b in ants_a
                has_a_for_b = a in ants_b
                print(f"  {b} in _ant_dict[{a}] ? {has_b_for_a}")
                print(f"  {a} in _ant_dict[{b}] ? {has_a_for_b}")
                print(f"  get_antonyms({a})[:4] = {get_antonyms(a)[:4]}")
                print(f"  get_antonyms({b})[:4] = {get_antonyms(b)[:4]}")
                if has_b_for_a and has_a_for_b:
                    print("SUCCESS: Bidirectional!")
                else:
                    print("STILL ONE-WAY")
                found = True
                break
if not found:
    print("No —— pair found in file.")

# Extra: check the specific user example if present
for w in ["熱", "冷"]:
    ants = get_antonyms(w)
    print(f"{w} antonyms (first 5): {ants[:5]}")

print("=== Test script finished ===")
