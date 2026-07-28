import { GENERATED_ZH_HANS } from './generated/zh-hans.generated.mjs';
import { selectUiCatalog } from './ui-locale.mjs';

const WORKBENCH_COPY = {
  zh: {
    returnToSearch: '返回搜尋首頁',
    filtering: '正篩選候選',
    filterCountHidden: '啟用篩選時不顯示未篩選候選數。',
    routeBackFailed: '暫時無法回到查韻；請再試一次。',
    noDraft: '尚未建立句格。',
    blankLock: '空白格不能鎖定；請先有字面、通配或碼。',
    locksCleared: '已解除全部鎖定。',
    readingFailed: '詞庫暫未就緒；句稿已建立，可繼續編輯並稍後重試。',
    storageFailed: '這次未能自動保存；句稿仍可繼續編輯。',
    readingsPartial: '部分字未有收錄讀音；你仍可鎖定字位或改用碼起句。',
    readingsReady: '已解析逐字讀音；請點擊鎖定替換段。',
    insertNoSpan: '無法插入：工作台沒有已鎖範圍；請改用取代整句。',
    inserted: '已插入字面到選段；請確認讀音。',
    ingestInvalid: '放入的字面無法建立句格。',
    ingested: '已從搜尋放入字面；請點擊鎖定替換段。',
    tooLong: '一句最多 64 格。',
    invalidInput: '請輸入原句、數字碼、平仄，或漢字與數字混合（如能夠44）；平仄勿同漢字／碼混寫。',
    createdCode: '已按碼建立空白句格，不會自動填入字面；請點擊碼格鎖定並查看候選。',
    createdMixed: '已建立混合句格；請點擊鎖定一至四格以查看候選。',
    createdSurface: '句格已建立；請點擊鎖定一至四格以查看候選。',
    manualSurface: '已手改一字；正在對齊讀音。',
    manualCode: '已手改為碼格。',
    cleared: '已清空句格。',
    spanRequired: '請先鎖定替換段。',
    spanApplied: '已手打替換段。',
    undoChange: '已復原最近一次改動。',
    undoClear: '已復原清空前的句稿。',
    searchOpenFailed: '無法打開搜尋頁。',
    createSentence: '建立句格',
    undoClearTitle: '復原清空前的句稿',
    undo: '復原',
    spanWidth: '須為 {count} 格（漢字或 ?）',
    noSelection: '尚未鎖定替換段；候選會在你鎖定後出現。',
    organizingCandidates: '正在整理候選…',
    candidatesUnavailable: '候選暫時不可用；句稿不受影響。',
    relaxEyebrow: '零結果時只改一項',
    relaxTitle: '可選放寬：{kind}',
    relaxEstimate: '預計可找到 {count} 項；不會自動採用。',
    relaxConfirm: '確認採用這項放寬',
    emptyHelp: '貼入你正在寫的一句，或先用碼與平仄搭起空白格；有字後點擊即可鎖定替換段。',
    returnInputAria: '回到建立句格輸入欄',
    returnInput: '↑ 回到輸入',
  },
  zhHans: GENERATED_ZH_HANS.workbench,
  en: {
    returnToSearch: 'Back to search home',
    filtering: 'Filtering candidates',
    filterCountHidden: 'Candidate count is hidden while filters are active.',
    routeBackFailed: 'Could not return to Rhyme Search yet. Please try again.',
    noDraft: 'Create a sentence grid first.',
    blankLock: 'A blank cell cannot be locked. Add a character, wildcard, or code first.',
    locksCleared: 'All locks cleared.',
    readingFailed: 'The lexicon is not ready yet. Your draft is safe; keep editing and retry later.',
    storageFailed: 'This draft could not be saved automatically, but you can keep editing it.',
    readingsPartial: 'Some characters have no recorded reading. You can still lock cells or start from codes.',
    readingsReady: 'Character readings resolved. Tap cells to lock a replacement span.',
    insertNoSpan: 'Cannot insert: no span is locked. Replace the whole sentence instead.',
    inserted: 'Text inserted into the selected span. Please confirm the readings.',
    ingestInvalid: 'The supplied text cannot form a sentence grid.',
    ingested: 'Text added from search. Tap cells to lock a replacement span.',
    tooLong: 'A sentence can contain at most 64 cells.',
    invalidInput: 'Enter a sentence, digit code, tone pattern, or mixed characters and digits (for example 能夠44). Do not mix tone symbols with characters or codes.',
    createdCode: 'Blank code grid created without inventing text. Tap code cells to lock a span and view candidates.',
    createdMixed: 'Mixed grid created. Lock one to four cells to view candidates.',
    createdSurface: 'Sentence grid created. Lock one to four cells to view candidates.',
    manualSurface: 'Character updated. Aligning its reading.',
    manualCode: 'Cell changed to a code.',
    cleared: 'Sentence grid cleared.',
    spanRequired: 'Lock a replacement span first.',
    spanApplied: 'Replacement span entered manually.',
    undoChange: 'Latest change undone.',
    undoClear: 'Cleared draft restored.',
    searchOpenFailed: 'Could not open the search page.',
    createSentence: 'Create grid',
    undoClearTitle: 'Restore the cleared draft',
    undo: 'Undo',
    spanWidth: 'Enter exactly {count} cells (characters or ?)',
    noSelection: 'No replacement span is locked. Candidates appear after you lock one.',
    organizingCandidates: 'Preparing candidates…',
    candidatesUnavailable: 'Candidates are temporarily unavailable; your draft is unaffected.',
    relaxEyebrow: 'Change one constraint after zero results',
    relaxTitle: 'Optional relaxation: {kind}',
    relaxEstimate: 'About {count} candidates may match. This will not be applied automatically.',
    relaxConfirm: 'Apply this relaxation',
    emptyHelp: 'Paste a sentence you are writing, or start with codes and tones. Once cells contain content, tap them to lock a replacement span.',
    returnInputAria: 'Return to the sentence-grid input',
    returnInput: '↑ Back to input',
  },
};

export function getWorkbenchCopy(lang = 'zh') {
  return selectUiCatalog(WORKBENCH_COPY, lang);
}

export function formatWorkbenchCopy(template, values = {}) {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll(`{${key}}`, String(value)),
    template,
  );
}

export function workbenchI18nSelfCheck() {
  const keys = Object.keys(WORKBENCH_COPY.zh);
  for (const lang of ['zhHans', 'en']) {
    if (Object.keys(WORKBENCH_COPY[lang]).join('\0') !== keys.join('\0')) {
      throw new Error(`workbench ${lang} structure`);
    }
  }
  if (getWorkbenchCopy('zh-Hans').filtering !== '正在筛选候选') throw new Error('workbench zh-Hans');
  if (getWorkbenchCopy('en').filtering !== 'Filtering candidates') throw new Error('workbench en');
}
