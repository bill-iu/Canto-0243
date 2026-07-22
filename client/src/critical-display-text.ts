/**
 * SSOT for Canto Critical Serif glyph coverage (offline display slogans).
 * build-fonts.ts subsets Noto Serif TC with this text; self-check guards drift.
 * Add every user-visible CJK slogan that uses the critical serif stack here.
 */
import { WORKBENCH_INTRO } from './workbench/intro-copy.ts';

/** Header hero (zh) — header-hero.tsx */
const HEADER_HERO_ZH = ['ONE·搵·韻', '格律／協音／押韻／近反義，一步搵到。'] as const;

/** About display slogans (zh) — shared/about-i18n.mjs */
const ABOUT_SLOGANS_ZH = [
  '即使離線，亦完全可用。',
  '呢一次，拎返你嘅創作主導權。',
  '關於 Canto-0243',
  'ONE·搵·韻 — 離線粵語填詞查找工作台。',
] as const;

/** Ready-gate / shell fragments historically in critical subset */
const SHELL_DISPLAY_ZH = ['即使離線亦完全可用', '呢一次拎返你嘅創作主導權'] as const;

function workbenchIntroZh(): string[] {
  const z = WORKBENCH_INTRO.zh;
  return [z.eyebrow, z.h1, z.h2];
}

/** Full string passed to Google Fonts `text=` (order irrelevant; unique chars suffice). */
export function criticalDisplayText(): string {
  const parts = [
    ...workbenchIntroZh(),
    ...HEADER_HERO_ZH,
    ...ABOUT_SLOGANS_ZH,
    ...SHELL_DISPLAY_ZH,
    // punctuation / brand marks used in slogans
    '·／，。—',
  ];
  const seen = new Set<string>();
  let out = '';
  for (const part of parts) {
    for (const ch of part) {
      if (!seen.has(ch)) {
        seen.add(ch);
        out += ch;
      }
    }
  }
  return out;
}

/** Slogans that must remain covered (for self-check; full phrases). */
export function criticalDisplayPhrases(): string[] {
  return [
    ...workbenchIntroZh(),
    ...HEADER_HERO_ZH,
    ...ABOUT_SLOGANS_ZH,
  ];
}
