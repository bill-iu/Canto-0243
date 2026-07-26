const MESSAGES = {
  zh: {
    'detail.title': '詞條詳情',
    'detail.close': '關閉詞條詳情',
    'detail.loading': '載入中…',
    'detail.putWorkbench': '放入句格',
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
    'detail.pos': '詞性',
    'detail.noSources': '—',
    'detail.noRelations': '—',
  },
  zhHans: {
    'detail.title': '词条详情',
    'detail.close': '关闭词条详情',
    'detail.loading': '载入中…',
    'detail.putWorkbench': '放入句格',
    'detail.readings.n': '{n}个读音',
    'detail.reading': '读音{n}',
    'detail.copy': '复制字面',
    'detail.copy.done': '已复制',
    'detail.phonetic': '语音音韵结构',
    'detail.initials': '声母',
    'detail.finals': '韵母',
    'detail.tone': '声调',
    'detail.tone.0243': '0243 码',
    'detail.tone.02493': '02493 码',
    'detail.length': '词条字数',
    'detail.corpusWeight': '语料库权重',
    'detail.sources': '词典出处',
    'detail.syns': '近义词',
    'detail.ants': '反义词',
    'detail.pos': '词性',
    'detail.noSources': '—',
    'detail.noRelations': '—',
  },
  en: {
    'detail.loading': 'Loading…',
    'detail.putWorkbench': 'Put in workbench',
    'detail.pos': 'Part of speech',
  },
};

export function tDetail(key, lang = 'zh', vars = {}) {
  const table = MESSAGES[lang === 'zh' ? 'zh' : lang === 'zh-Hans' ? 'zhHans' : lang] ?? {};
  let text = table[key] ?? MESSAGES.zh[key] ?? key;
  for (const [name, value] of Object.entries(vars)) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}
