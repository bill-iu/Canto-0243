# Quickstart Validation: 平仄模式

## Prerequisites

- Work from `D:\Canto-0243` on the `dev` branch.
- Install the repository's Python and client dependencies.
- Build or load the normal test lexicon used by existing query journey tests.

## Validate behavior

1. Start the client and select 平仄模式.
2. Verify `PZ?` and `?PZ` return only three-position candidates that satisfy their P/Z positions.
3. Verify `PZ3` under each sub-mode. Its P/Z positions remain unchanged, while its numeric position follows that sub-mode's existing pure-code behavior.
4. Verify `PZ好=` and `?PZ好=` retain the existing `好=` rhyme-anchor semantics.
5. Attempt a Jyutping anchor in 平仄模式 and verify the clear unsupported-mode hint.
6. Switch to a normal mode and verify `p`, `z`, `pa` and `zoeng` are handled as Jyutping with no automatic mode switch.
7. Copy a `mode=pz&pzmode=m2` URL, reopen it, switch tabs and use back/forward; verify mode, sub-mode and query all restore together.

## Automated checks

Run the focused Python tests after implementation:

```powershell
python -m unittest tests.test_ping_ze_serial tests.smoke.test_mode_detect_parity tests.smoke.test_query_journey tests.smoke.test_position_match_invariants
```

Run portable state checks:

```powershell
node --test tests/query_tabs_state_test.mjs
```

Run the client parser and PWA shell self-checks from `client`:

```powershell
cmd.exe /c npx tsx scripts/parser-self-check.ts
cmd.exe /c npx tsx scripts/pwa-p4-search-shell-self-check.ts
```

Run the normal client lint/build checks required by the changed files before handoff.
