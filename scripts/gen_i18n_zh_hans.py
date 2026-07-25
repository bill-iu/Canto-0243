"""Generate zh-Hans i18n content for shared/*-i18n.mjs and app-context.mjs."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    import opencc
except ImportError:
    raise SystemExit("Missing opencc-python-reimplemented. Run: pip install -r requirements-dev.txt")

CONVERTER = opencc.OpenCC("t2s")

SRC_FILES = [
    REPO_ROOT / "shared" / "app-context.mjs",
    REPO_ROOT / "shared" / "mode-i18n.mjs",
    REPO_ROOT / "shared" / "about-i18n.mjs",
    REPO_ROOT / "shared" / "guide-i18n.mjs",
    REPO_ROOT / "shared" / "entry-detail-i18n.mjs",
]


def t2s(text: str) -> str:
    return CONVERTER.convert(text)


def t2s_q(m: re.Match) -> str:
    raw = m.group(0)
    q = raw[0]
    content = raw[1:-1]
    return q + t2s(content) + q


def t2s_all_strings_in_block(text: str) -> str:
    text = re.sub(r"'[^']*'", t2s_q, text)
    text = re.sub(r'"[^"]*"', t2s_q, text)
    text = re.sub(r"`[^`]*`", t2s_q, text)
    return text


# --- file-specific generators ---

def gen_app_context(source: str) -> str:
    # Find the MESSAGES zh block, t2s it, insert as zhHans
    def replace_msg(m: re.Match) -> str:
        zh_block = m.group(1)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"  zh: {{ {zh_block.strip()} }},\n  zh-Hans: {{ {zh_hans.strip()} }},\n  en: {{ {m.group(2).strip()} }}"

    source = re.sub(
        r"  zh: \{ (.+) \},\n  en: \{ (.+) \}",
        replace_msg,
        source,
        count=1,
    )

    # Fallback: match multiline version
    if "zh-Hans" not in source:
        def replace_msg_ml(m: re.Match) -> str:
            zh_block = m.group(1)
            en_block = m.group(2)
            zh_hans = t2s_all_strings_in_block(zh_block)
            return f"  zh: {{\n{zh_block}\n  }},\n  zh-Hans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }}"

        source = re.sub(
            r"  zh: \{\n(.+?)\n  \},\n  en: \{\n(.+?)\n  \}",
            replace_msg_ml,
            source,
            count=1,
            flags=re.DOTALL,
        )

    # Update getLang
    source = source.replace(
        "if (saved === 'zh' || saved === 'en') return saved;",
        "if (saved === 'zh' || saved === 'zh-Hans' || saved === 'en') return saved;",
    )
    source = source.replace(
        "document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : 'en';",
        "document.documentElement.lang = lang === 'zh' ? 'zh-Hant' : lang === 'zh-Hans' ? 'zh-Hans' : 'en';",
    )

    return source


def gen_mode_i18n(source: str) -> str:
    # Extract MODE_META, t2s it, insert MODE_META_ZH_HANS
    m = re.search(r"(export const MODE_META = \{[^;]+\};)", source)
    if m and "MODE_META_ZH_HANS" not in source:
        zh_hans = t2s_all_strings_in_block(m.group(1))
        zh_hans = zh_hans.replace("export const MODE_META =", "export const MODE_META_ZH_HANS =")
        source = source.replace(m.group(1), m.group(1) + "\n" + zh_hans)

    # Update getModeMeta
    source = source.replace(
        "const table = lang === 'en' ? MODE_META_EN : MODE_META;",
        "const table = lang === 'en' ? MODE_META_EN : lang === 'zh-Hans' ? MODE_META_ZH_HANS : MODE_META;",
    )

    # Update typedef
    source = source.replace(
        "/** @typedef {'zh' | 'en'} UiLang */",
        "/** @typedef {'zh' | 'zh-Hans' | 'en'} UiLang */",
    )

    return source


def gen_about_i18n(source: str) -> str:
    # Find the ABOUT_COPY zh block, t2s it, insert zhHans
    def replace_about(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"zh: {{\n{zh_block}\n  }},\n  zhHans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }}"

    source = re.sub(
        r"zh: \{\n(.+?)\n  \},\n  en: \{\n(.+?)\n  \}",
        replace_about,
        source,
        count=1,
        flags=re.DOTALL,
    )

    # Update getAboutCopy
    source = source.replace(
        "return ABOUT_COPY[lang === 'en' ? 'en' : 'zh'];",
        "return ABOUT_COPY[lang === 'en' ? 'en' : lang === 'zh-Hans' ? 'zhHans' : 'zh'];",
    )

    return source


def gen_guide_i18n(source: str) -> str:
    # Patch resolveLang
    source = source.replace(
        "return lang === 'en' ? 'en' : 'zh';",
        "return lang === 'en' ? 'en' : lang === 'zh-Hans' ? 'zhHans' : 'zh';",
    )

    # Insert zhHans keys into each section
    def patch_section(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"zh: {{\n{zh_block}\n    }},\n    zhHans: {{\n{zh_hans}\n    }},\n    en: {{\n{en_block}\n    }}"

    source = re.sub(
        r"    zh: \{\n(.+?)\n    \},\n    en: \{\n(.+?)\n    \}",
        patch_section,
        source,
        flags=re.DOTALL,
    )

    # GUIDE_HERO
    def patch_hero(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"zh: {{\n{zh_block}\n  }},\n  zhHans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }}"

    # GUIDE_HERO — optional trailing comma before };
    hero_re = re.compile(r"const GUIDE_HERO = \{\n  zh: \{\n(.+?)\n  \},\n  en: \{\n(.+?)\n  \},?\n\};", re.DOTALL)
    def patch_hero(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"const GUIDE_HERO = {{\n  zh: {{\n{zh_block}\n  }},\n  zhHans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }},\n}};"
    source = hero_re.sub(patch_hero, source, count=1)

    # GUIDE_INTRO
    intro_re = re.compile(r"const GUIDE_INTRO = \{\n  zh: \{\n(.+?)\n  \},\n  en: \{\n(.+?)\n  \},?\n\};", re.DOTALL)
    def patch_intro(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"const GUIDE_INTRO = {{\n  zh: {{\n{zh_block}\n  }},\n  zhHans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }},\n}};"
    source = intro_re.sub(patch_intro, source, count=1)

    # GUIDE_GROUP_LABEL
    def patch_group(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s(zh_block)
        return f"zh: {{ {zh_block} }},\n  zhHans: {{ {zh_hans} }},\n  en: {{ {en_block} }}"

    source = re.sub(
        r"const GUIDE_GROUP_LABEL = \{\n  zh: \{ ([^}]+) \},\n  en: \{ ([^}]+) \},\n\};",
        lambda m: f"const GUIDE_GROUP_LABEL = {{\n  {patch_group(m)}\n}};",
        source,
        count=1,
    )

    # GUIDE_TOC_COPY
    def patch_toc(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s(zh_block)
        return f"zh: {{ {zh_block} }},\n  zhHans: {{ {zh_hans} }},\n  en: {{ {en_block} }}"

    source = re.sub(
        r"const GUIDE_TOC_COPY = \{\n  zh: \{ ([^}]+) \},\n  en: \{ ([^}]+) \},\n\};",
        lambda m: f"const GUIDE_TOC_COPY = {{\n  {patch_toc(m)}\n}};",
        source,
        count=1,
    )

    return source


def gen_entry_detail(source: str) -> str:
    # MESSAGES = { zh: { ... }, en: { ... } }; — insert zhHans
    def replace_msg(m: re.Match) -> str:
        zh_block = m.group(1)
        en_block = m.group(2)
        zh_hans = t2s_all_strings_in_block(zh_block)
        return f"zh: {{\n{zh_block}\n  }},\n  zhHans: {{\n{zh_hans}\n  }},\n  en: {{\n{en_block}\n  }}"

    source = re.sub(
        r"zh: \{\n(.+?)\n  \},\n  en: \{\n(.+?)\n  \}",
        replace_msg,
        source,
        count=1,
        flags=re.DOTALL,
    )

    # Update tDetail
    source = source.replace(
        "const table = MESSAGES[lang] ?? {};",
        "const table = MESSAGES[lang === 'zh' ? 'zh' : lang === 'zh-Hans' ? 'zhHans' : lang] ?? {};",
    )

    return source


def main() -> int:
    generators = {
        "app-context.mjs": gen_app_context,
        "mode-i18n.mjs": gen_mode_i18n,
        "about-i18n.mjs": gen_about_i18n,
        "guide-i18n.mjs": gen_guide_i18n,
        "entry-detail-i18n.mjs": gen_entry_detail,
    }

    for path in SRC_FILES:
        name = path.name
        gen = generators.get(name)
        if not gen:
            print(f"Skipping {name} — no generator")
            continue

        original = path.read_text(encoding="utf-8")
        updated = gen(original)
        if original == updated:
            print(f"No change: {name}")
            continue

        path.write_text(updated, encoding="utf-8")
        print(f"Updated: {name}")

    print("Done.")

    # Generate t2s-char-map.mjs for runtime headword conversion
    print("\nGenerating shared/t2s-char-map.mjs...")
    t2s_map = {}
    for cp in range(0x4E00, 0x9FFF + 1):
        char = chr(cp)
        converted = CONVERTER.convert(char)
        if converted != char:
            t2s_map[char] = converted
    for cp in range(0x3400, 0x4DBF + 1):
        char = chr(cp)
        converted = CONVERTER.convert(char)
        if converted != char:
            t2s_map[char] = converted

    map_path = REPO_ROOT / "shared" / "t2s-char-map.mjs"
    with open(map_path, "w", encoding="utf-8") as f:
        f.write("export default ")
        json.dump(t2s_map, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"Wrote {map_path} ({len(t2s_map)} mappings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
