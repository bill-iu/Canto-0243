import type { GuideLang, GuideMode } from './guide-examples';

interface GuideQuickExample {
  query: string;
  mode: GuideMode;
  labelZh: string;
  labelEn: string;
}

export interface GuideQuickRow {
  keys: string[];
  titleZh: string;
  titleEn: string;
  blurbZh: string;
  blurbEn: string;
  examples: GuideQuickExample[];
}

interface GuideQuickWideColumn {
  rows: GuideQuickRow[];
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
      { query: '23', mode: '0243', labelZh: '找同音字', labelEn: 'Same-tone matches' },
      { query: '45', mode: '394052', labelZh: '六聲碼', labelEn: '394052 mode' },
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
      { query: '23@手', mode: '0243', labelZh: '字面錨', labelEn: 'Literal @ anchor' },
      { query: '香=?', mode: '0243', labelZh: '首字同韻', labelEn: 'First slot rhyme' },
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
      { query: '3_', mode: '0243', labelZh: '首格同 3 同音', labelEn: 'First slot code 3' },
      { query: '23?', mode: '0243', labelZh: '頭兩格同碼', labelEn: 'First two slots code' },
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
      { query: 'PZ好=', mode: 'pingze', labelZh: '平仄＋韻母錨', labelEn: 'PZ + rhyme anchor' },
      { query: '=好PZ', mode: 'pingze', labelZh: '韻母錨＋平仄', labelEn: 'Rhyme anchor + PZ' },
    ],
  },
  {
    keys: ['~', '!', '~~', '!!'],
    titleZh: '近反義',
    titleEn: 'Synonym / antonym',
    blurbZh: '近義（~）、反義（!）、二字複合（~~／!!）。',
    blurbEn: 'Near (~), antonym (!), two-char compounds (~~ / !!).',
    examples: [
      { query: '!苦悶', mode: '0243', labelZh: '反義', labelEn: 'Antonym' },
      { query: '~~', mode: '0243', labelZh: '近義複合', labelEn: 'Syn compound' },
      { query: '!!', mode: '0243', labelZh: '反義複合', labelEn: 'Ant compound' },
      { query: '~開心', mode: '0243', labelZh: '近義', labelEn: 'Near-synonym' },
    ],
  },
];

/** ≥1024px 兩欄 — 每欄多段 row（標題＋說明＋例），垂直填滿 */
const GUIDE_QUICK_WIDE_COLUMNS: GuideQuickWideColumn[] = [
  {
    rows: [
      {
        keys: ['0-9'],
        titleZh: '旋律與長度',
        titleEn: 'Melody & length',
        blurbZh: '用 0243／02493／394052 碼搵同音詞。',
        blurbEn: 'Match tones with 0243 / 02493 / 394052 codes.',
        examples: [
          { query: '23', mode: '0243', labelZh: '找同音字', labelEn: 'Same-tone matches' },
          { query: '93', mode: '02493', labelZh: '五聲分清', labelEn: '02493 mode' },
          { query: '45', mode: '394052', labelZh: '六聲碼', labelEn: '394052 mode' },
          { query: '0234', mode: '0243', labelZh: '四字同碼', labelEn: '4-slot code' },
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
          { query: 'PZ好=', mode: 'pingze', labelZh: '平仄＋韻母錨', labelEn: 'PZ + rhyme anchor' },
        ],
      },
      {
        keys: ['=', '+', '@'],
        titleZh: '語音與錨',
        titleEn: 'Phonetics & anchors',
        blurbZh: '同韻／同聲（=）、加號錨（+）、字面錨（@）。',
        blurbEn: 'Rhyme/initial (=), plus anchor (+), literal (@).',
        examples: [
          { query: '就=', mode: '0243', labelZh: '同韻', labelEn: 'Same rhyme' },
          { query: '23+好=', mode: '0243', labelZh: '加號錨', labelEn: 'Plus anchor' },
          { query: '23@手', mode: '0243', labelZh: '字面錨', labelEn: 'Literal @ anchor' },
          { query: '香=?', mode: '0243', labelZh: '首字同韻', labelEn: 'First slot rhyme' },
        ],
      },
      {
        keys: ['='],
        titleZh: '串列韻／聲錨',
        titleEn: 'Serial rhyme / initial',
        blurbZh: '連續數字：每位一音節碼；{碼}{字}= 比韻。',
        blurbEn: 'Consecutive digits: one code per syllable; {code}{char}= matches rhyme.',
        examples: [
          { query: '23就=', mode: '0243', labelZh: '二字串列韻', labelEn: '2-slot serial rhyme' },
          { query: '04困=49倒=', mode: '0243', labelZh: '四字串列韻', labelEn: '4-slot serial rhyme' },
          { query: '04=困49=倒', mode: '0243', labelZh: '四字串列聲', labelEn: '4-slot serial initial' },
        ],
      },
    ],
  },
  {
    rows: [
      {
        keys: ['?', '_', '%'],
        titleZh: '通配與遮罩',
        titleEn: 'Wildcards & masks',
        blurbZh: '缺字／通配格；可混數字碼同固定漢字。',
        blurbEn: 'Missing slots; mix digit codes with fixed characters.',
        examples: [
          { query: '+香??', mode: '0243', labelZh: '缺字', labelEn: 'Mask' },
          { query: '?30人', mode: '0243', labelZh: '通配碼', labelEn: 'Wildcard code' },
          { query: '3_', mode: '0243', labelZh: '首格同 3 同音', labelEn: 'First slot code 3' },
          { query: '23?', mode: '0243', labelZh: '頭兩格同碼', labelEn: 'First two slots code' },
        ],
      },
      {
        keys: ['?'],
        titleZh: '部分／前綴通配',
        titleEn: 'Partial / prefix wildcard',
        blurbZh: '通配格標缺字；前綴 ? 表示首格任意。',
        blurbEn: 'Wildcard slots for gaps; leading ? fully wildcards slot 1.',
        examples: [
          { query: '窮?潦倒=', mode: '0243', labelZh: '部分韻錨', labelEn: 'Partial rhyme anchor' },
          { query: '?香港=', mode: '0243', labelZh: '前綴通配等號', labelEn: 'Prefix wildcard equals' },
          { query: '?=困潦倒', mode: '0243', labelZh: '前綴通配聲', labelEn: 'Prefix wildcard initial' },
        ],
      },
      {
        keys: ['a-z'],
        titleZh: '粵拼',
        titleEn: 'Jyutping',
        blurbZh: '粵拼查字；拉丁字母可標韻母、音節或聲母錨。',
        blurbEn: 'Jyutping lookup; Latin marks finals, syllables, or initials.',
        examples: [
          { query: 'nei hou', mode: '0243', labelZh: '粵拼查詢', labelEn: 'Jyutping lookup' },
          { query: '3hon4', mode: '0243', labelZh: '音節錨', labelEn: 'Syllable anchor' },
          { query: '3$漢4', mode: '0243', labelZh: '漢字音節錨', labelEn: 'Hanzi syllable anchor' },
          { query: '23o', mode: '0243', labelZh: '韻母錨', labelEn: 'Final anchor' },
        ],
      },
      {
        keys: ['~', '!', '~~', '!!'],
        titleZh: '近反義',
        titleEn: 'Synonym / antonym',
        blurbZh: '近義（~）、反義（!）、二字複合（~~／!!）。',
        blurbEn: 'Near (~), antonym (!), two-char compounds (~~ / !!).',
        examples: [
          { query: '!苦悶', mode: '0243', labelZh: '反義', labelEn: 'Antonym' },
          { query: '~~', mode: '0243', labelZh: '近義複合', labelEn: 'Syn compound' },
          { query: '!!', mode: '0243', labelZh: '反義複合', labelEn: 'Ant compound' },
          { query: '~開心', mode: '0243', labelZh: '近義', labelEn: 'Near-synonym' },
        ],
      },
    ],
  },
];

export interface GuideQuickProps {
  lang: GuideLang;
  disabled?: boolean;
  onPick: (query: string, mode: GuideMode) => void;
  onOpenFullGuide: () => void;
}

function GuideQuickExampleButton({
  ex,
  en,
  disabled,
  onPick,
}: {
  ex: GuideQuickExample;
  en: boolean;
  disabled: boolean;
  onPick: (query: string, mode: GuideMode) => void;
}) {
  return (
    <button
      type="button"
      className="guide-quick__example"
      disabled={disabled}
      title={en ? ex.labelEn : ex.labelZh}
      onClick={() => onPick(ex.query, ex.mode)}
    >
      <code translate="no">{ex.query}</code>
      <span>{en ? ex.labelEn : ex.labelZh}</span>
    </button>
  );
}

function GuideQuickRowBlock({
  row,
  en,
  disabled,
  onPick,
  inColumn = false,
}: {
  row: GuideQuickRow;
  en: boolean;
  disabled: boolean;
  onPick: (query: string, mode: GuideMode) => void;
  inColumn?: boolean;
}) {
  const Tag = inColumn ? 'div' : 'li';
  return (
    <Tag className={`guide-quick__row${inColumn ? ' guide-quick__row--in-column' : ''}`}>
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
            <GuideQuickExampleButton
              key={`${ex.query}-${ex.mode}`}
              ex={ex}
              en={en}
              disabled={disabled}
              onPick={onPick}
            />
          ))}
        </div>
      </div>
    </Tag>
  );
}

export function GuideQuick({ lang, disabled = false, onPick, onOpenFullGuide }: GuideQuickProps) {
  const en = lang === 'en';
  return (
    <section className="guide-quick" aria-labelledby="guideQuickTitle">
      <header className="guide-quick__header">
        <div className="guide-quick__title-row">
          <h2 id="guideQuickTitle">{en ? 'How to use' : '教你點用'}</h2>
          <button type="button" className="ghost-button guide-quick__cta" onClick={onOpenFullGuide}>
            {en ? 'Full guide' : '完整說明'}
          </button>
        </div>
      </header>
      <ul className="guide-quick__rows">
        {GUIDE_QUICK_ROWS.map((row) => (
          <GuideQuickRowBlock
            key={row.keys.join(',')}
            row={row}
            en={en}
            disabled={disabled}
            onPick={onPick}
          />
        ))}
      </ul>
      <div className="guide-quick__columns">
        {GUIDE_QUICK_WIDE_COLUMNS.map((col, colIdx) => (
          <div key={colIdx} className="guide-quick__column">
            {col.rows.map((row) => (
              <GuideQuickRowBlock
                key={row.titleZh}
                row={row}
                en={en}
                disabled={disabled}
                onPick={onPick}
                inColumn
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
