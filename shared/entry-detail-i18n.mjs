const MESSAGES = {
  zh: {
    'detail.title': '詞條詳情',
    'detail.close': '關閉詞條詳情',
    'detail.readings.n': '{n}個讀音',
    'detail.reading': '讀音{n}',
    'detail.copy': '複製字面',
    'detail.copy.done': '已複製',
    'detail.phonetic': '語音音韻結構',
    'detail.initials': '聲母',
    'detail.finals': '韻母',
    'detail.tone': '聲調',
    'detail.tone.0243': '0243 碼',
    'detail.tone.02493': '02493 碼',
    'detail.length': '詞條字數',
    'detail.corpusWeight': '語料庫權重',
    'detail.sources': '詞典出處',
    'detail.syns': '近義詞',
    'detail.ants': '反義詞',
    'detail.noSources': '—',
    'detail.noRelations': '—',
  },
  en: {},
};

export function tDetail(key, lang = 'zh', vars = {}) {
  const table = MESSAGES[lang] ?? {};
  let text = table[key] ?? MESSAGES.zh[key] ?? key;
  for (const [name, value] of Object.entries(vars)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}