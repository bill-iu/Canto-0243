/** 模式文案 — port of frontend/app-context.mjs MODE_META */
export type UiMode = '0243' | '02493' | 'synonym';
export type UrlMode = 'm1' | 'm2' | 'syn';

export interface ModeMeta {
  title: string;
  note: string;
  readout: string;
  statsLabel: string;
  placeholder: string;
}

export const MODE_META: Record<UrlMode, ModeMeta> = {
  m1: {
    title: '0243模式',
    note: '鬆',
    readout: '0243模式（鬆）',
    statsLabel: '0243模式 · 鬆',
    placeholder: '搵嘢：0243／漢字／粵拼',
  },
  m2: {
    title: '02493模式',
    note: '緊',
    readout: '02493模式（緊）',
    statsLabel: '02493模式 · 緊',
    placeholder: '搵嘢：02493／漢字／粵拼',
  },
  syn: {
    title: '近反義',
    note: '查',
    readout: '近反義模式（查）',
    statsLabel: '近反義 · 查',
    placeholder: '打字搵同義／反義',
  },
};

export function uiModeToUrlMode(mode: UiMode): UrlMode {
  if (mode === '02493') return 'm2';
  if (mode === 'synonym') return 'syn';
  return 'm1';
}

export function urlModeToUiMode(mode: string | null | undefined): UiMode {
  if (mode === 'm2') return '02493';
  if (mode === 'syn') return 'synonym';
  return '0243';
}

export function modeMetaFor(uiMode: UiMode): ModeMeta {
  return MODE_META[uiModeToUrlMode(uiMode)];
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p4-search-shell-self-check.ts` */
export function modeMetaSelfCheck(): void {
  if (modeMetaFor('0243').readout !== '0243模式（鬆）') {
    throw new Error('modeMetaSelfCheck: m1 readout');
  }
  if (uiModeToUrlMode('02493') !== 'm2' || urlModeToUiMode('m2') !== '02493') {
    throw new Error('modeMetaSelfCheck: m2 roundtrip');
  }
  if (uiModeToUrlMode('synonym') !== 'syn' || urlModeToUiMode('syn') !== 'synonym') {
    throw new Error('modeMetaSelfCheck: syn roundtrip');
  }
}
