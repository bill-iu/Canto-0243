import type { OfflineReadinessStatus } from './hooks/useDB.tsx';

const GATE_NEAR_DONE_PCT = 92;

export function formatPwaGateLabel(
  offlineStatus: OfflineReadinessStatus,
  progress: number,
  opts: { isOnline: boolean; isDbCached: boolean | null; errorMessage?: string },
): string {
  if (offlineStatus === 'ready') return '開得工！';
  if (offlineStatus === 'failed') {
    return opts.errorMessage ? `離線就緒失敗：${opts.errorMessage}` : '離線就緒失敗';
  }
  if (offlineStatus === 'not_ready') {
    if (!opts.isOnline) {
      return opts.isDbCached ? '偵測到離線緩存，重試初始化…' : '離線未就緒，需連網完成一次就緒';
    }
    return '執緊啲字…';
  }
  const pct = Math.max(0, Math.min(100, Math.round(progress)));
  if (pct >= GATE_NEAR_DONE_PCT) return `差啲就齊… ${pct}%`;
  if (pct > 0) return `執緊啲字… ${pct}%`;
  return '執緊啲字…';
}
