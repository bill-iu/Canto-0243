# Hyperframes Composition Brief: Canto-0243

## Objective
Create a short Traditional Chinese launch-style brag video for Canto-0243.

## Output
- Composition directory: `brag-output/composition/`
- Rendered video: `brag-output/brag.mp4`
- Format: landscape, 1920x1080
- Duration: 21 seconds

## Source Material
- Project root: `D:\Canto-0243`
- Primary files read: `client/src/App.tsx`, `frontend/open-design.css`, `frontend/shell.css`, `client/index.html`, `client/package.json`, `README.md`
- Product name: Canto-0243
- Tagline / strongest claim: 用 0243、粵拼、押韻、近反義，一步搵詞
- Key UI or visual moment to recreate: PWA search panel with query explanation and result cards
- Copy that must appear verbatim:
  - Canto-0243
  - ONE-RUN-RHYME
  - 填詞卡住？
  - 125,262 詞條
  - 粵語填詞，唔使慢慢撞字。

## Creative Direction
- Tone preset: polished
- Creative direction: 繁中粵語創作工具 launch film，暖色、利落、帶少少詩性
- Interpretation: Keep the video serious and readable; let the specificity of the query syntax carry the personality.
- Angle: A Cantonese songwriter's command center, not a generic dictionary.
- Hook: Start from the real pain of writing lyrics and needing the next word immediately.
- Outro / punchline: Canto-0243 as the calm tool that stops the slow manual hunt.
- Avoid:
  - Generic SaaS language
  - Abstract filler visuals
  - Random AI imagery
  - Rushed unreadable Chinese text

## Visual Identity
- Background: #EBDFD0
- Text: #161716
- Accent: #8A5A20
- Ink accent: #9F1239
- Display font: Playfair Display / Noto Serif TC
- Body font: Noto Sans TC
- Mono font: JetBrains Mono
- Visual references from the project: warm PWA canvas, rounded search field, pill mode controls, tab strip, serif hero, mono code snippets, ink-red brand mark

## Storyboard
Use `brag-output/brag-plan.md` as the creative contract.

Scene summary:
1. Hook, 3s:「填詞卡住？」plus query tokens.
2. Search Doing The Work, 4s: PWA search mockup, `香港=`, query explanation.
3. Results, 4s: result cards with word, jyutping, code, plus 125,262 metric.
4. Syntax Surface, 5s: mode chips and examples build a command board.
5. Outro, 5s: Canto-0243 lockup and final line.

## Audio
- Audio role: warm bed with sparse professional accents
- Audio arc: bed starts immediately, UI ticks support middle scenes, final bell lands the logo
- Music: `happy-beats-business-moves-vol-9-by-ende-dot-app.mp3`
- Music treatment: 0.28 volume, fade down in final 1.2s
- Music cue guidance: bundled cue preset; strong cues around 4.23s, 6.34s, 10.54s, 12.65s; use only if readability survives
- Audio-reactive treatment: subtle or none; if implemented, only the ink mark and warm glow breathe
- Audio-coupled moments:
  - Scene 1: typed query tokens
  - Scene 2: simulated submit tap
  - Scene 3: card-by-card results
  - Scene 4: mode chips
  - Scene 5: final logo
- SFX selection guidance: low-risk click/drop/soft impact/bell sounds
- SFX analysis guidance: `C:\Users\User\.codex\skills\brag\assets\sfx\sfx-analysis.md`
- Exact SFX choice: chosen locally in `composition/assets/sfx/`
- Audio files: copied into `brag-output/composition/assets/`

## Hyperframes Instructions
Use a standalone HyperFrames composition with direct root clips, local fonts, local audio, and deterministic WAAPI animations. Run HyperFrames lint, validate, inspect, snapshot, and render where possible.

Requirements:
- Show at least one real UI, copy, or visual element from the source project.
- Keep all text readable in the final render.
- Keep the video within 15-25 seconds.
- Include the planned music/SFX layer.
- Avoid external runtime/media dependencies in the composition.
