/** 模式文案 — shared with shared/mode-i18n.mjs */
import {
  MODE_META as MODE_META_ZH,
  getModeMeta as getSharedModeMeta,
  modeHelp as sharedModeHelp,
  modeRedirectHint as sharedModeRedirectHint,
} from '../../shared/mode-i18n.mjs';
import { uiModeToUrlMode as contractUiModeToUrlMode, urlModeToUiMode as contractUrlModeToUiMode } from '../../contracts/search-mode-manifest.mjs';

export type UiMode = '0243' | '02493' | '394052' | 'synonym' | 'pingze';
export type UrlMode = 'm1' | 'm2' | 'm3' | 'syn' | 'pz';
export type PingzeSubMode = 'm1' | 'm2' | 'm3';
export type UiLang = 'zh' | 'zh-Hans' | 'en';
export type Last0243SearchMode = '0243' | '02493' | '394052';

export interface ModeMeta {
  title: string;
  note: string;
  readout: string;
  statsLabel: string;
  placeholder: string;
}

export const MODE_META: Record<UrlMode, ModeMeta> = MODE_META_ZH;

export function uiModeToUrlMode(mode: UiMode): UrlMode {
  return contractUiModeToUrlMode(mode) as UrlMode;
}

export function urlModeToUiMode(mode: string | null | undefined): UiMode {
  return contractUrlModeToUiMode(mode) as UiMode;
}

export function last0243UiToUrlMode(mode: Last0243SearchMode): 'm1' | 'm2' | 'm3' {
  if (mode === '02493') return 'm2';
  if (mode === '394052') return 'm3';
  return 'm1';
}

export function getModeMeta(urlMode: UrlMode, lang: UiLang = 'zh'): ModeMeta {
  return getSharedModeMeta(urlMode, lang);
}

export function modeMetaFor(uiMode: UiMode, lang: UiLang = 'zh'): ModeMeta {
  return getModeMeta(uiModeToUrlMode(uiMode), lang);
}

export function modeHelp(uiMode: UiMode, lang: UiLang = 'zh'): string {
  return sharedModeHelp(uiModeToUrlMode(uiMode), lang);
}

export function modeRedirectHint(mode: 'm1' | 'm2' | 'm3', lang: UiLang = 'zh'): string {
  return sharedModeRedirectHint(mode, lang);
}

/** ponytail: runnable self-check — `npx tsx client/scripts/pwa-p4-search-shell-self-check.ts` */
export function modeMetaSelfCheck(): void {
  if (modeMetaFor('0243').readout !== '0243模式（鬆）') {
    throw new Error('modeMetaSelfCheck: zh m1 readout');
  }
  if (modeMetaFor('02493', 'en').readout !== '02493 Mode (Strict)') {
    throw new Error('modeMetaSelfCheck: en m2 readout');
  }
  if (modeMetaFor('394052').readout !== '394052模式（六聲）') {
    throw new Error('modeMetaSelfCheck: zh m3 readout');
  }
  if (modeMetaFor('synonym', 'en').title !== 'Near-Antonyms') {
    throw new Error('modeMetaSelfCheck: en syn title');
  }
  if (uiModeToUrlMode('02493') !== 'm2' || urlModeToUiMode('m2') !== '02493') {
    throw new Error('modeMetaSelfCheck: m2 roundtrip');
  }
  if (uiModeToUrlMode('394052') !== 'm3' || urlModeToUiMode('m3') !== '394052') {
    throw new Error('modeMetaSelfCheck: m3 roundtrip');
  }
  if (uiModeToUrlMode('synonym') !== 'syn' || urlModeToUiMode('syn') !== 'synonym') {
    throw new Error('modeMetaSelfCheck: syn roundtrip');
  }
}
