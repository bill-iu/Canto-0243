/**
 * Guard: every critical slogan CJK char is covered by criticalDisplayText() SSOT.
 * Run: node --experimental-strip-types scripts/critical-display-self-check.ts
 */
import { criticalDisplayPhrases, criticalDisplayText } from '../src/critical-display-text.ts';
import { WORKBENCH_INTRO } from '../src/workbench/intro-copy.ts';

const text = criticalDisplayText();
const covered = new Set([...text]);

for (const phrase of criticalDisplayPhrases()) {
  for (const ch of phrase) {
    if (/\s/.test(ch)) continue;
    if (!covered.has(ch)) {
      throw new Error(`critical-display missing glyph for «${ch}» (from «${phrase}»)`);
    }
  }
}

// Workbench intro zh must be in SSOT (regression for system-font fallback)
for (const s of Object.values(WORKBENCH_INTRO.zh)) {
  for (const ch of s) {
    if (/\s/.test(ch)) continue;
    if (!covered.has(ch)) {
      throw new Error(`intro-copy char «${ch}» not in criticalDisplayText`);
    }
  }
}

if (!text.includes('授') || !text.includes('漁') || !text.includes('萬')) {
  throw new Error('expected new intro glyphs 授/漁/萬 in critical set');
}

console.log(`critical-display self-check ok (${covered.size} unique chars)`);
