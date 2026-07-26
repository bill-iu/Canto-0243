import { selectUiCatalog } from './ui-locale.mjs';

const PORTABLE_EXIT_COPY = {
  zh: {
    confirm: '將關閉本機服務，未儲存工作唔會遺失。確定停止本機服務？',
    fail: '無法關閉本機服務。請稍後再試，或使用工作管理員結束 pythonw.exe。',
    done: 'Canto-0243 已停止。你可以關閉此分頁。',
  },
  zhHans: {
    confirm: '将关闭本机服务，未保存工作不会丢失。确定停止本机服务？',
    fail: '无法关闭本机服务。请稍后再试，或使用任务管理器结束 pythonw.exe。',
    done: 'Canto-0243 已停止。你可以关闭此分页。',
  },
  en: {
    confirm: 'This will stop the local server. Unsaved work is already on disk. Stop the local service?',
    fail: 'Could not stop the local server. Try again, or end pythonw.exe in Task Manager.',
    done: 'Canto-0243 has stopped. You can close this tab.',
  },
};

export function getPortableExitCopy(lang = 'zh') {
  return selectUiCatalog(PORTABLE_EXIT_COPY, lang);
}

export function portableExitI18nSelfCheck() {
  if (getPortableExitCopy('zh').done !== 'Canto-0243 已停止。你可以關閉此分頁。') throw new Error('portable exit zh');
  if (getPortableExitCopy('zh-Hans').done !== 'Canto-0243 已停止。你可以关闭此分页。') throw new Error('portable exit zh-Hans');
  if (getPortableExitCopy('en').confirm.startsWith('This will stop') !== true) throw new Error('portable exit en');
}
