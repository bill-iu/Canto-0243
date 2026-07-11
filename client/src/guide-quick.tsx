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
      { query: '0234', mode: '0243', labelZh: '四字同聲調碼', labelEn: 'Four-character tones' },
      { query: '93', mode: '02493', labelZh: '五聲分清', labelEn: '02493 mode' },
      { query: '23', mode: '0243', labelZh: '找同音字', labelEn: 'Same-tone matches' },
      { query: '45', mode: '394052', labelZh: '六聲碼', labelEn: '394052 mode' },
    ],
  },
  {
    keys: ['=', '+', '@', '$'],
    titleZh: '同韻／同聲／加長',
    titleEn: 'Rhyme / initial / lengthen',
    blurbZh: '同韻／同聲（=）、用 + 加長、@ 定實某個字、$ 疊字。',
    blurbEn: 'Rhyme/initial (=), + to lengthen, @ to lock a character, $ for reduplication.',
    examples: [
      { query: '香=', mode: '0243', labelZh: '同韻', labelEn: 'Same rhyme' },
      { query: '23+好=', mode: '0243', labelZh: '用 + 加長同韻', labelEn: 'Lengthen with +' },
      { query: '23@手', mode: '0243', labelZh: '定實尾字', labelEn: 'Lock last character' },
      { query: '香=?', mode: '0243', labelZh: '頭字同韻', labelEn: 'First character rhymes' },
    ],
  },
  {
    keys: ['?', '_', '%'],
    titleZh: '留空某啲字',
    titleEn: 'Leave some characters open',
    blurbZh: '唔知嘅位留空；可以混聲調數字同定實嘅漢字。',
    blurbEn: 'Leave unknowns open; mix tone digits with fixed characters.',
    examples: [
      { query: '+香??', mode: '0243', labelZh: '頭字定實，其餘留空', labelEn: 'Lock first; leave rest open' },
      { query: '?30人', mode: '0243', labelZh: '頭字任意＋數字＋尾同韻', labelEn: 'Any first + digits + last rhymes' },
      { query: '3_', mode: '0243', labelZh: '頭字同 3 同音', labelEn: 'First tone 3' },
      { query: '23?', mode: '0243', labelZh: '頭兩字同碼', labelEn: 'First two tones' },
    ],
  },
  {
    keys: ['P', 'Z'],
    titleZh: '平仄',
    titleEn: 'Ping–ze',
    blurbZh: 'P＝平、Z＝仄；數字＝嗰個字要同呢個聲調同音。',
    blurbEn: 'P = ping, Z = ze; a digit locks that character\'s tone.',
    examples: [
      { query: 'PZ', mode: 'pingze', labelZh: '二字平仄', labelEn: 'Two-character PZ' },
      { query: 'PZ3', mode: 'pingze', labelZh: '平仄＋碼', labelEn: 'PZ + digit' },
      { query: 'PZ好=', mode: 'pingze', labelZh: '平仄＋尾字同韻', labelEn: 'PZ + last rhymes' },
      { query: '=好PZ', mode: 'pingze', labelZh: '頭字同聲＋平仄', labelEn: 'First initial + PZ' },
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
          { query: '0234', mode: '0243', labelZh: '四字同聲調碼', labelEn: 'Four-character tones' },
        ],
      },
      {
        keys: ['P', 'Z'],
        titleZh: '平仄',
        titleEn: 'Ping–ze',
        blurbZh: 'P＝平、Z＝仄；數字＝嗰個字要同呢個聲調同音。',
        blurbEn: 'P = ping, Z = ze; a digit locks that character\'s tone.',
        examples: [
          { query: 'PZ', mode: 'pingze', labelZh: '二字平仄', labelEn: 'Two-character PZ' },
          { query: 'PZ3', mode: 'pingze', labelZh: '平仄＋碼', labelEn: 'PZ + digit' },
          { query: 'PZ好=', mode: 'pingze', labelZh: '平仄＋尾字同韻', labelEn: 'PZ + last rhymes' },
        ],
      },
      {
        keys: ['=', '+', '@'],
        titleZh: '同韻／同聲／加長',
        titleEn: 'Rhyme / initial / lengthen',
        blurbZh: '同韻／同聲（=）、用 + 加長、@ 定實某個字。',
        blurbEn: 'Rhyme/initial (=), + to lengthen, @ to lock a character.',
        examples: [
          { query: '香=', mode: '0243', labelZh: '同韻', labelEn: 'Same rhyme' },
          { query: '23+好=', mode: '0243', labelZh: '用 + 加長同韻', labelEn: 'Lengthen with +' },
          { query: '23@手', mode: '0243', labelZh: '定實尾字', labelEn: 'Lock last character' },
          { query: '香=?', mode: '0243', labelZh: '頭字同韻', labelEn: 'First character rhymes' },
        ],
      },
      {
        keys: ['='],
        titleZh: '多重同韻／同聲',
        titleEn: 'Multi-slot rhyme / initial',
        blurbZh: '連續打數字＝每個字一個聲調；字後加 = 就同韻。',
        blurbEn: 'Digits in a row = one tone each; char= means same rhyme.',
        examples: [
          { query: '23香=', mode: '0243', labelZh: '二字：尾字同韻', labelEn: 'Two chars: last rhymes' },
          { query: '04困=49倒=', mode: '0243', labelZh: '四字：指定位置同韻', labelEn: 'Four chars: locked rhymes' },
          { query: '04=困49=倒', mode: '0243', labelZh: '四字：指定位置同聲', labelEn: 'Four chars: locked initials' },
        ],
      },
    ],
  },
  {
    rows: [
      {
        keys: ['?', '_', '%'],
        titleZh: '留空某啲字',
        titleEn: 'Leave some characters open',
        blurbZh: '唔知嘅位留空；可以混聲調數字同定實嘅漢字。',
        blurbEn: 'Leave unknowns open; mix tone digits with fixed characters.',
        examples: [
          { query: '+香??', mode: '0243', labelZh: '頭字定實，其餘留空', labelEn: 'Lock first; leave rest open' },
          { query: '?30人', mode: '0243', labelZh: '頭字任意＋數字＋尾同韻', labelEn: 'Any first + digits + last rhymes' },
          { query: '3_', mode: '0243', labelZh: '頭字同 3 同音', labelEn: 'First tone 3' },
          { query: '23?', mode: '0243', labelZh: '頭兩字同碼', labelEn: 'First two tones' },
        ],
      },
      {
        keys: ['?'],
        titleZh: '留空／頭字任意',
        titleEn: 'Gaps / any first character',
        blurbZh: '用 ? 留空；開頭 ? 表示第一個字隨便。',
        blurbEn: 'Use ? for gaps; leading ? means any first character.',
        examples: [
          { query: '窮?潦倒=', mode: '0243', labelZh: '中間留空、其餘同韻', labelEn: 'Gap in middle; others rhyme' },
          { query: '?香港=', mode: '0243', labelZh: '頭字任意、其餘同韻', labelEn: 'Any first; rest rhyme' },
          { query: '?=困潦倒', mode: '0243', labelZh: '頭字任意、其餘同聲', labelEn: 'Any first; rest same initial' },
        ],
      },
      {
        keys: ['a-z'],
        titleZh: '粵拼',
        titleEn: 'Jyutping',
        blurbZh: '粵拼查字；亦可用字母指定某個字嘅韻／聲／音節。',
        blurbEn: 'Jyutping lookup; letters can set a character\'s rhyme, syllable, or initial.',
        examples: [
          { query: 'nei hou', mode: '0243', labelZh: '粵拼查詢', labelEn: 'Jyutping lookup' },
          { query: '3hon4', mode: '0243', labelZh: '指定音節', labelEn: 'Set syllable' },
          { query: '3$漢4', mode: '0243', labelZh: '用漢字標音節', labelEn: 'Hanzi marks syllable' },
          { query: '23o', mode: '0243', labelZh: '指定韻母', labelEn: 'Set rhyme' },
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
