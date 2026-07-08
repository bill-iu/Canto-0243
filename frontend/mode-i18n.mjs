/** Shared search-mode labels — portable + PWA (zh default + en i18n). */

/** @typedef {'m1' | 'm2' | 'm3' | 'syn'} UrlMode */
/** @typedef {'zh' | 'en'} UiLang */

/** @type {Record<UrlMode, { title: string; note: string; readout: string; statsLabel: string; placeholder: string }>} */
export const MODE_META = {
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
  m3: {
    title: '394052模式',
    note: '矩陣',
    readout: '394052模式（矩陣）',
    statsLabel: '394052模式 · 矩陣',
    placeholder: '搵嘢：394052／漢字／粵拼',
  },
  syn: {
    title: '近反義',
    note: '查',
    readout: '近反義模式（查）',
    statsLabel: '近反義 · 查',
    placeholder: '打字搵同義／反義',
  },
};

/** @type {typeof MODE_META} */
const MODE_META_EN = {
  m1: {
    title: '0243 Mode',
    note: 'Loose',
    readout: '0243 Mode (Loose)',
    statsLabel: '0243 Mode · Loose',
    placeholder: 'Search: 0243 / characters / Jyutping',
  },
  m2: {
    title: '02493 Mode',
    note: 'Strict',
    readout: '02493 Mode (Strict)',
    statsLabel: '02493 Mode · Strict',
    placeholder: 'Search: 02493 / characters / Jyutping',
  },
  m3: {
    title: '394052 Mode',
    note: 'Matrix',
    readout: '394052 Mode (Matrix)',
    statsLabel: '394052 Mode · Matrix',
    placeholder: 'Search: 394052 / characters / Jyutping',
  },
  syn: {
    title: 'Near-Antonyms',
    note: 'Browse',
    readout: 'Near-Antonym Mode (Browse)',
    statsLabel: 'Near-Antonyms · Browse',
    placeholder: 'Type synonyms / antonyms',
  },
};

/**
 * @param {string} mode
 * @param {UiLang} [lang]
 */
export function getModeMeta(mode, lang = 'zh') {
  const key = mode in MODE_META ? /** @type {UrlMode} */ (mode) : 'm1';
  const table = lang === 'en' ? MODE_META_EN : MODE_META;
  return table[key] ?? table.m1;
}

/**
 * @param {UrlMode} mode
 * @param {UiLang} [lang]
 */
export function modeHelp(mode, lang = 'zh') {
  if (mode === 'm1') {
    return lang === 'en' ? 'Common 0243 codes & mixed queries' : '常用 0243 編碼與混合查詢';
  }
  if (mode === 'm2') {
    return lang === 'en' ? '02493 codes (distinguish 2nd tone)' : '02493 碼（分清二聲）';
  }
  if (mode === 'm3') {
    return lang === 'en' ? '394052 matrix — strict tone digits' : '394052 矩陣碼（三／五聲分明）';
  }
  return lang === 'en' ? 'Synonyms, antonyms & semantically related' : '近義、反義與語意相關';
}

/**
 * @param {'m1' | 'm2' | 'm3'} mode
 * @param {UiLang} [lang]
 */
export function modeRedirectHint(mode, lang = 'zh') {
  const key = mode === 'm2' ? 'm2' : mode === 'm3' ? 'm3' : 'm1';
  const meta = getModeMeta(key, lang);
  if (lang === 'en') {
    return `This syntax switched to ${meta.readout} for search`;
  }
  return `此語法已切換至 ${meta.readout} 查詢`;
}

/** @param {UiLang} [lang] */
export function syncPortableModeMenu(lang = 'zh') {
  for (const mode of /** @type {UrlMode[]} */ (['m1', 'm2', 'm3', 'syn'])) {
    const btn = document.querySelector(`[data-mode="${mode}"].mode-option`);
    if (!btn) continue;
    const meta = getModeMeta(mode, lang);
    const nameEl = btn.querySelector('.mode-name');
    const helpEl = btn.querySelector('.mode-help');
    if (nameEl) {
      nameEl.innerHTML = `${meta.title}<span class="mode-note">${meta.note}</span>`;
    }
    if (helpEl) helpEl.textContent = modeHelp(mode, lang);
  }
}

/** ponytail: runnable self-check — `node frontend/mode-i18n.mjs` */
export function modeI18nSelfCheck() {
  if (getModeMeta('m1').readout !== '0243模式（鬆）') {
    throw new Error('modeI18nSelfCheck: zh m1 readout');
  }
  if (getModeMeta('m2', 'en').readout !== '02493 Mode (Strict)') {
    throw new Error('modeI18nSelfCheck: en m2 readout');
  }
  if (getModeMeta('syn', 'en').title !== 'Near-Antonyms') {
    throw new Error('modeI18nSelfCheck: en syn title');
  }
  if (!modeRedirectHint('m1', 'en').includes('0243 Mode (Loose)')) {
    throw new Error('modeI18nSelfCheck: en redirect hint');
  }
  if (getModeMeta('m3').readout !== '394052模式（矩陣）') {
    throw new Error('modeI18nSelfCheck: zh m3 readout');
  }
}

// ponytail: guard process — bare `process.argv` crashes browser bundles that import this module
if (typeof process !== 'undefined' && import.meta.url === `file://${process.argv[1]?.replace(/\\/g, '/')}`) {
  modeI18nSelfCheck();
  console.log('mode-i18n self-check: ok');
}