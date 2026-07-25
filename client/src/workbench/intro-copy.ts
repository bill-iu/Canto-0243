/**
 * Locked workbench intro titles (grill 2026-07-21).
 * zh brand stack + en pair; no body paragraph under h2.
 */
export const WORKBENCH_INTRO = {
  zh: {
    eyebrow: '創作由你主導',
    h1: '授漁·句格工作台',
    h2: '一行拆解，萬種可能',
  },
  en: {
    eyebrow: 'Creation stays in your hands',
    h1: 'VerseCraft Workbench',
    h2: 'One line taken apart — endless options',
  },
} as const;

export function workbenchIntroCopy(lang: 'zh' | 'zh-Hans' | 'en') {
  return WORKBENCH_INTRO[lang === 'zh-Hans' ? 'zh' : lang];
}
