import type { GuideLang, GuideMode } from './guide-examples';

interface GuideQuickRow {
  keys: string[];
  titleZh: string;
  titleEn: string;
  blurbZh: string;
  blurbEn: string;
  examples: Array<{ query: string; mode: GuideMode; labelZh: string; labelEn: string }>;
}

/** 搜尋教學速覽 — guide-i18n subset，唔另開 SSOT */
const GUIDE_QUICK_ROWS: GuideQuickRow[] = [
  {
    keys: ['0-9'],
    titleZh: '旋律與長度',
    titleEn: 'Melody & length',
    blurbZh: '用選定嘅 0243／02493／394052 碼搵同音詞（如 0243、93、45）。',
    blurbEn: 'Match tones with the selected 0243 / 02493 / 394052 code (e.g. 0243, 93, 45).',
    examples: [
      { query: '0234', mode: '0243', labelZh: '四字同碼', labelEn: '4-slot code' },
      { query: '93', mode: '02493', labelZh: '五聲分清', labelEn: '02493 mode' },
    ],
  },
  {
    keys: ['=', '+', '@', '$'],
    titleZh: '語音與錨',
    titleEn: 'Phonetics & anchors',
    blurbZh: '同韻／同聲（=）、加號錨（+）、字面錨（@）、疊韻（$）。',
    blurbEn: 'Rhyme/initial (=), plus anchor (+), literal (@), doubled ($).',
    examples: [
      { query: '就=', mode: '0243', labelZh: '同韻', labelEn: 'Same rhyme' },
      { query: '23+好=', mode: '0243', labelZh: '加號錨', labelEn: 'Plus anchor' },
    ],
  },
  {
    keys: ['?', '_', '%'],
    titleZh: '通配與遮罩',
    titleEn: 'Wildcards & masks',
    blurbZh: '缺字／通配格；可混數字碼同固定漢字。',
    blurbEn: 'Missing slots; mix digit codes with fixed characters.',
    examples: [
      { query: '+香??', mode: '0243', labelZh: '缺字', labelEn: 'Mask' },
      { query: '?30人', mode: '0243', labelZh: '通配碼', labelEn: 'Wildcard code' },
    ],
  },
  {
    keys: ['P', 'Z'],
    titleZh: '平仄',
    titleEn: 'Ping–ze',
    blurbZh: 'P＝平、Z＝仄；數字格跟子模式同音。',
    blurbEn: 'P = ping, Z = ze; digits follow the sub-mode.',
    examples: [
      { query: 'PZ', mode: 'pingze', labelZh: '平仄二字', labelEn: 'Two-slot PZ' },
      { query: 'PZ3', mode: 'pingze', labelZh: '平仄＋碼', labelEn: 'PZ + digit' },
    ],
  },
  {
    keys: ['~', '!', '~~', '!!'],
    titleZh: '近反義',
    titleEn: 'Synonym / antonym',
    blurbZh: '近義（~）、反義（!）、二字複合（~~／!!）。',
    blurbEn: 'Near (~), antonym (!), two-char compounds (~~ / !!).',
    examples: [
      { query: '~開心', mode: '0243', labelZh: '近義', labelEn: 'Near-synonym' },
      { query: '~~', mode: '0243', labelZh: '近義複合', labelEn: 'Syn compound' },
    ],
  },
];

export interface GuideQuickProps {
  lang: GuideLang;
  disabled?: boolean;
  onPick: (query: string, mode: GuideMode) => void;
  onOpenFullGuide: () => void;
}

export function GuideQuick({ lang, disabled = false, onPick, onOpenFullGuide }: GuideQuickProps) {
  const en = lang === 'en';
  return (
    <section className="guide-quick" aria-labelledby="guideQuickTitle">
      <header className="guide-quick__header">
        <h2 id="guideQuickTitle">{en ? 'Quick syntax' : '快速語法指南'}</h2>
        <p className="guide-quick__lede">
          {en
            ? 'Combine these operators for advanced search.'
            : '組合以下運算符以進行進階搜尋。'}
        </p>
        <button type="button" className="ghost-button guide-quick__cta" onClick={onOpenFullGuide}>
          {en ? 'Open full search guide' : '查看搜尋教學完整說明'}
        </button>
      </header>
      <ul className="guide-quick__rows">
        {GUIDE_QUICK_ROWS.map((row) => (
          <li key={row.keys.join(',')} className="guide-quick__row">
            <div className="guide-quick__keys" aria-hidden>
              {row.keys.map((key) => (
                <span key={key} className="guide-quick__key">
                  {key}
                </span>
              ))}
            </div>
            <div className="guide-quick__body">
              <h3>{en ? row.titleEn : row.titleZh}</h3>
              <p>{en ? row.blurbEn : row.blurbZh}</p>
              <div className="guide-quick__examples">
                {row.examples.map((ex) => (
                  <button
                    key={`${ex.query}-${ex.mode}`}
                    type="button"
                    className="guide-quick__example"
                    disabled={disabled}
                    title={en ? ex.labelEn : ex.labelZh}
                    onClick={() => onPick(ex.query, ex.mode)}
                  >
                    <code translate="no">{ex.query}</code>
                    <span>{en ? ex.labelEn : ex.labelZh}</span>
                  </button>
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
