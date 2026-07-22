# ADR-0063: Repository text files use LF line endings

Windows vibe-coding / agents often rewrite files as CRLF, which then shows up as whole-file noise diffs against LF history. We standardize on LF for all text (including `.bat`), keep binaries untouched, and auto-fix staged files on commit.

## Decision

1. **`.gitattributes`**: `* text=auto eol=lf`, plus explicit `binary` for common media / wasm / db / archive extensions. Existing `portable/macos/*` LF rules stay.
2. **`.editorconfig`**: `end_of_line = lf` so editors and agents prefer LF when saving.
3. **Pre-commit**: committed `.githooks/pre-commit` runs `scripts/fix_eol_lf.py --staged` (CRLF/CR → LF, re-stage). Install with `python scripts/install_githooks.py` (copies into `.git/hooks`; does not change `core.hooksPath`).
4. **One-time**: `git add --renormalize .` so the index matches LF; land that as its own commit when applying this ADR.
5. **`.bat`**: no CRLF exception — `portable/START.bat` is already LF in-tree and is the production Windows launcher.

## Considered

| Option | Result |
|--------|--------|
| Leave mixed / no rule | Reject — recurring pollution |
| CRLF for Windows-only | Reject — dual-port + macOS portable need LF |
| Husky + Prettier just for EOL | Reject — YAGNI; root has no Node package |
| Hook only rejects CRLF | Reject — auto-fix matches agent workflow |

## Consequences

- After renormalize, expect a large EOL-only commit; review with ignore-whitespace.
- New clones should run `python scripts/install_githooks.py` once (documented in git-workflow).
- Agents should not fight the hook by reintroducing CRLF; if a tool must write CRLF temporarily, the hook repairs on commit.
