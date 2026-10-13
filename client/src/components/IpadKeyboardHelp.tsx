import { useState } from 'react';
import type { KeyboardRecoveryResult } from '../ipad-keyboard';
import './ipad-keyboard-help.css';

const COPY = {
  zh: {
    title: '鍵盤異常？',
    description: '只剩浮動鍵盤或叫唔出鍵盤？可先重建搜尋框，再用手指點入；唔會清除搜尋文字、查詢分頁或離線詞庫。',
    reset: '重建搜尋框',
    ready: '搜尋框已重建。請用手指點上方搜尋框，唔好用 Apple Pencil。',
    composing: '正在組字，暫未重建。請先完成選字，再試一次。',
    unavailable: '搜尋框暫未就緒，請稍後再試。',
    limit: '此操作無法強制完整鍵盤或關閉隨手寫。若仍然卡住：設定 → Apple Pencil → 關閉「隨手寫」，儲存其他工作後重新啟動 iPad。唔需要刪除 App 或網站資料。',
  },
  'zh-Hans': {
    title: '键盘异常？',
    description: '只剩浮动键盘或无法显示键盘？可先重建搜索框，再用手指点入；不会清除搜索文字、查询分页或离线词库。',
    reset: '重建搜索框',
    ready: '搜索框已重建。请用手指点上方搜索框，不要用 Apple Pencil。',
    composing: '正在组字，暂未重建。请先完成选字，再试一次。',
    unavailable: '搜索框暂未就绪，请稍后再试。',
    limit: '此操作无法强制完整键盘或关闭随手写。若仍然卡住：设置 → Apple Pencil → 关闭“随手写”，保存其他工作后重新启动 iPad。不需要删除 App 或网站数据。',
  },
  en: {
    title: 'Keyboard trouble?',
    description: 'Stuck with a floating keyboard or no keyboard? Recreate the search field, then tap it with a finger. Your search text, tabs and offline dictionary are kept.',
    reset: 'Recreate search field',
    ready: 'Search field recreated. Tap the field above with a finger, not Apple Pencil.',
    composing: 'Text composition is in progress. Finish choosing characters, then try again.',
    unavailable: 'The search field is not ready. Please try again shortly.',
    limit: 'This cannot force a full-size keyboard or turn off Scribble. If it stays stuck: Settings → Apple Pencil → turn off Scribble, save other work, then restart iPad. Do not delete the app or website data.',
  },
};

export function IpadKeyboardHelp({ lang, onRecover }: {
  lang: keyof typeof COPY;
  onRecover: () => KeyboardRecoveryResult;
}) {
  const [result, setResult] = useState<KeyboardRecoveryResult | null>(null);
  const copy = COPY[lang];
  return (
    <details className="ipad-keyboard-help">
      <summary>{copy.title}</summary>
      <p>{copy.description}</p>
      <button type="button" onClick={() => setResult(onRecover())}>{copy.reset}</button>
      <p role="status" aria-live="polite">{result ? copy[result] : ''}</p>
      <p>{copy.limit}</p>
    </details>
  );
}
