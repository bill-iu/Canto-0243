#!/usr/bin/env python
# Convert guotong chinese_dictionary (simp) to trad, format for the project's thesaurus loaders.
import opencc
import os

def convert_file(in_path, out_path, converter):
    with open(in_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    trad_content = converter.convert(content)
    # Ensure output dir
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(trad_content)
    print(f"Converted {in_path} -> {out_path} (len={len(trad_content)} chars)")

if __name__ == '__main__':
    # s2t: Simplified to Traditional (general)
    # Use 's2t' ; for Taiwan style could use 's2tw' but 's2t' is fine and matches previous samples.
    converter = opencc.OpenCC('s2t')
    base = 'data/thesaurus'
    convert_file(f'{base}/dict_synonym_simp.txt', f'{base}/dict_synonym.txt', converter)
    convert_file(f'{base}/dict_antonym_simp.txt', f'{base}/dict_antonym.txt', converter)
    print("Done. Now test with: python -c \"from utils import get_synonyms, get_antonyms; print(get_synonyms('開心')[:5]); print(get_antonyms('開心')[:5])\"")
