/**
 * PWA 搜尋教學 — 範例 manifest（對齊桌面 guide-card + family 覆蓋）
 */
import { getGuideSections as getI18nSections } from '../../frontend/guide-i18n.mjs';

export const GUIDE_FAMILY_IDS = [
  'word_lookup',
  'jyutping_lookup',
  'digit_code',
  'mode_02493',
  'mode_394052',
  'code_char',
  'literal_ref',
  'wildcard_code_anchor',
  'rhyme_initial_anchor',
  'plus_anchor',
  'serial_phoneme',
  'partial_rhyme',
  'partial_initial',
  'prefix_wildcard_equals',
  'prefix_wildcard_initial',
  'mask_query',
  'equals_query',
  'code_sandwich_equals',
  'jyutping_anchor_initial',
  'jyutping_anchor_final',
  'jyutping_anchor_syllable',
  'hanzi_syllable_anchor',
  'relation_lookup',
  'compound_syn',
  'compound_ant',
  'compound_doubled',
  'heteronym_code',
  'connective_compound',
  'syn_pool',
] as const;

export type GuideFamilyId = (typeof GUIDE_FAMILY_IDS)[number];
export type GuideMode = '0243' | '02493' | '394052' | 'synonym' | 'pingze';
export type GuideLang = 'zh' | 'en';

export interface GuideExample {
  query: string;
  mode: GuideMode;
  label: string;
  familyId?: GuideFamilyId;
  title?: string;
}

export interface GuideSection {
  id: string;
  title: string;
  intro: string;
  examples: GuideExample[];
}

/** Self-check family tags keyed by section id + query */
const FAMILY_BY_KEY: Partial<Record<string, GuideFamilyId>> = {
  'basic:就': 'word_lookup',
  'basic:nei hou': 'jyutping_lookup',
  'digit:23': 'digit_code',
  'digit:93': 'mode_02493',
  'digit:45': 'mode_394052',
  'serial:23就=': 'code_char',
  'serial:04困=49倒=': 'serial_phoneme',
  'partial:窮?潦倒=': 'partial_rhyme',
  'partial:=窮?潦倒': 'partial_initial',
  'prefix-wildcard:?香港=': 'prefix_wildcard_equals',
  'prefix-wildcard:?=困潦倒': 'prefix_wildcard_initial',
  'wildcard-code:?30人': 'wildcard_code_anchor',
  'mask:+香??': 'mask_query',
  'plus:23@手': 'literal_ref',
  'plus:23+好=': 'plus_anchor',
  'rhyme-initial:就=': 'rhyme_initial_anchor',
  'jyutping-anchor:3hon4': 'jyutping_anchor_syllable',
  'jyutping-anchor:3$漢4': 'hanzi_syllable_anchor',
  'jyutping-anchor:3h4': 'jyutping_anchor_initial',
  'jyutping-anchor:23o': 'jyutping_anchor_final',
  'equals:香港=': 'equals_query',
  'equals:2我=3': 'code_sandwich_equals',
  'relation:!苦悶': 'relation_lookup',
  'syn-pool:開心': 'syn_pool',
  'compound-syn:~~': 'compound_syn',
  'compound-ant:!!': 'compound_ant',
  'doubled:$$': 'compound_doubled',
  'heteronym:33/34': 'heteronym_code',
  'connective:!與!': 'connective_compound',
};

function uiModeToGuideMode(mode: string): GuideMode {
  if (mode === 'm2') return '02493';
  if (mode === 'm3') return '394052';
  if (mode === 'syn') return 'synonym';
  if (mode === 'pz') return 'pingze';
  return '0243';
}

export function getGuideSections(lang: GuideLang = 'zh'): GuideSection[] {
  return getI18nSections(lang).map((section) => ({
    id: section.id,
    title: section.title,
    intro: section.intro,
    examples: section.examples.map((ex) => {
      const item: GuideExample = {
        query: ex.query,
        mode: uiModeToGuideMode(ex.mode),
        label: ex.label,
      };
      const familyId = FAMILY_BY_KEY[`${section.id}:${ex.query}`];
      if (familyId) item.familyId = familyId;
      if (ex.title) item.title = ex.title;
      return item;
    }),
  }));
}

/** zh 預設（self-check 與既有匯入） */
export const GUIDE_SECTIONS: GuideSection[] = getGuideSections('zh');

export function allGuideExamples(): GuideExample[] {
  return GUIDE_SECTIONS.flatMap((section) => section.examples);
}

/** ponytail: coverage — `npx tsx client/scripts/pwa-guide-coverage-self-check.ts` */
export function guideCoverageSelfCheck(): void {
  const tagged = allGuideExamples().filter((ex) => ex.familyId);
  const seen = new Set(tagged.map((ex) => ex.familyId));
  const missing = GUIDE_FAMILY_IDS.filter((id) => !seen.has(id));
  if (missing.length) {
    throw new Error(`guideCoverageSelfCheck: missing families: ${missing.join(', ')}`);
  }
}
