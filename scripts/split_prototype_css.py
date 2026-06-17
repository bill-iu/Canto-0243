"""One-time migration: split inline CSS from prototype.html into open-design.css + index.css.

Source file was removed after E2 phase 1; re-run only if you restore inline styles.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
proto = (ROOT / "frontend" / "prototype.html").read_text(encoding="utf-8")
css = re.search(r"<style>(.*?)</style>", proto, re.S).group(1)

INDEX_ROOTS = (
    ".preload-overlay",
    ".gate-",
    "html[data-landing",
    "html.fonts-ready .gate",
    ".app-shell",
    ".landing-",
    ".hero",
    ".eyebrow",
    ".results",
    ".result-item",
    ".info",
    ".syn-",
    ".load-more",
    ".guide-",
    ".file-fallback",
    ".file-card",
    ".file-note",
)


def rule_targets_index(selector_part: str) -> bool:
    s = selector_part.strip()
    if not s or s.startswith("/*"):
        return False
    if "@keyframes" in s:
        name = s.split("{")[0]
        return any(k in name for k in ("gate-brand", "hero-settle", "search-rise"))
    if s.startswith("@media"):
        return False
    for sel in re.split(r",", s.split("{")[0]):
        sel = sel.strip()
        if not sel:
            continue
        if any(sel.startswith(r) or r in sel for r in INDEX_ROOTS):
            return True
    return False


def parse_rules(css_text: str) -> list[str]:
    rules = []
    i = 0
    n = len(css_text)
    while i < n:
        while i < n and css_text[i] in " \t\n\r":
            i += 1
        if i >= n:
            break
        start = i
        if css_text[i : i + 2] == "/*":
            end = css_text.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue
        depth = 0
        j = i
        started = False
        while j < n:
            c = css_text[j]
            if c == "{":
                depth += 1
                started = True
            elif c == "}":
                depth -= 1
                if started and depth == 0:
                    j += 1
                    break
            j += 1
        rules.append(css_text[start:j])
        i = j
    return rules


def dedent(s: str) -> str:
    lines = s.splitlines()
    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return s
    indent = min(len(ln) - len(ln.lstrip()) for ln in non_empty)
    return "\n".join(ln[indent:] if ln.strip() else "" for ln in lines)


rules = parse_rules(css)
open_rules: list[str] = []
index_rules: list[str] = []

for rule in rules:
    head = rule.split("{", 1)[0]
    if rule.strip().startswith("@media"):
        if any(
            x in rule
            for x in (
                ".hero",
                ".guide-",
                ".preload",
                ".gate-",
                ".landing",
                ".results",
                ".app-shell",
                ".search-panel.is-landing",
            )
        ):
            index_rules.append(rule)
        else:
            open_rules.append(rule)
    elif rule_targets_index(head):
        index_rules.append(rule)
    else:
        open_rules.append(rule)

open_css = (
    "/* Open Design · shared shell (index.html) */\n\n"
    + "\n\n".join(dedent(r).strip() for r in open_rules if r.strip())
    + "\n"
)
index_css = (
    "/* Canto-0243 · gate / hero / results / guide */\n\n"
    + "\n\n".join(dedent(r).strip() for r in index_rules if r.strip())
    + "\n"
)

(ROOT / "frontend" / "open-design.css").write_text(open_css, encoding="utf-8")
(ROOT / "frontend" / "index.css").write_text(index_css, encoding="utf-8")
print(f"rules={len(rules)} open={len(open_rules)} index={len(index_rules)}")
