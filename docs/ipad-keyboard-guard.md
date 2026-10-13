# iPad PWA keyboard guard (2026-10-13)

This is a best-effort mitigation, not a verified fix for a specific iPadOS bug. Physical iPad validation remains required.

## Incident and boundary

The installed Canto web app was stuck with a floating keyboard while Safari was normal. Relaunching the app did not help. Turning Scribble OFF **and then restarting the iPad** resolved it; these combined interventions do not identify a single root cause.

Standard WebKit form controls support Scribble. UIKit's native UIScribbleInteraction is not a PWA JavaScript API. Do not claim an HTML inputmode, viewport heuristic, pointer interception or readonly toggle can disable Scribble or force the full-size keyboard.

References:
- https://developer.apple.com/videos/play/wwdc2020/10106/
- https://developer.apple.com/documentation/uikit/uiscribbleinteraction
- https://bugs.webkit.org/show_bug.cgi?id=279904 (related missing-keyboard symptom, not confirmation of this incident)
- https://html.spec.whatwg.org/dev/interaction.html

## Behavior

- Only an installed iPad web app (including desktop-UA iPad) activates this helper. Safari tabs, Desktop/Portable, Android and iPhone are unaffected.
- On document hidden/pagehide, release focus only from the active main search input. Never refocus on resume, and never react to window blur or viewport resize. This is conservative input-session hygiene; prevention of the OS fault has not been demonstrated.
- Skip automatic release and manual recovery while that input is composing text. Do not touch workbench fields/drafts.
- The collapsed **鍵盤異常？ / Keyboard trouble?** entry offers **重建搜尋框 / Recreate search field**. It replaces only the search DOM input via an independent React key, retaining controlled text and query tabs. Startup/history-restore gates block recovery. Native selection/undo history may reset; the operation is deliberately user-triggered.
- The user then taps the field with a finger. The app reports that the FIELD was recreated, never that the system keyboard was fixed.
- If still stuck: Settings → Apple Pencil → Scribble OFF, save other work, then restart iPad. There is no storage clearing, automatic reload, service-worker removal, OPFS deletion, new telemetry or runtime dependency.

## Verification and release limits

`node --experimental-strip-types scripts/ipad-keyboard-self-check.ts`: **12 checks passed**. Platform gating, focus ownership, paired lifecycle events, composition safety, missing/disabled/readonly fields, remounted inputs and listener cleanup are exercised with test doubles. App wiring checks are structural. This does not exercise the native iPad keyboard.

The check is registered under `ci`, `pwa`, `local` in the self-check manifest. Existing `app-shell-i18n`, `ui-locale`, `portable-host-build` checks also passed. Direct Vite PWA and Portable bundling succeeded. Normal npm build wrapper failed because its Windows child shell could not find node; focused oxlint could not execute in that shell.

Full `tsc -b` remains unsuccessful, with diagnostics in untouched generated query registry, db modules and vite.config.ts. Local Pages artifact validation also fails: `lexicon-manifest.json sha256 does not match lyrics.db`. This patch does not alter dictionary data or suppress these checks. **Do not publish the local build artifacts as a validated release.**

Before production release, on a physical test iPad verify: background/resume retains `𡁻?0243香=` and tabs without auto-focus; manual reset retains the draft and needs a deliberate finger tap; Chinese composition, external keyboard, VoiceOver and workbench editing still work; the help is absent in Safari. Real-device Scribble comparisons and browser-rendered visual acceptance were not performed in this session.

Follow the repository's `dev` → owner-confirmed PR → `main` workflow. A dev source patch is not an automatic update to the installed production PWA. Resolve release checks before deployment.
