/** ADR-0032: 閘前進度 + 多 Tab 廣播（F） */

export type GatePhase = 'download' | 'open' | 'validate';

const DOWNLOAD_WEIGHT = 0.85;
const OPEN_WEIGHT = 0.1;
const VALIDATE_WEIGHT = 0.05;

const CHANNEL = 'canto-lexicon-gate-progress';

type Listener = (percent: number) => void;

const listeners = new Set<Listener>();
let channel: BroadcastChannel | null = null;

function phaseToPercent(phase: GatePhase, phase01: number): number {
  const t = Math.max(0, Math.min(1, phase01));
  if (phase === 'download') return Math.round(t * DOWNLOAD_WEIGHT * 100);
  if (phase === 'open') return Math.round((DOWNLOAD_WEIGHT + t * OPEN_WEIGHT) * 100);
  return Math.round((DOWNLOAD_WEIGHT + OPEN_WEIGHT + t * VALIDATE_WEIGHT) * 100);
}

function ensureChannel(): BroadcastChannel | null {
  if (typeof BroadcastChannel === 'undefined') return null;
  channel ??= new BroadcastChannel(CHANNEL);
  return channel;
}

export function reportGatePhase(phase: GatePhase, phase01: number): void {
  const percent = phaseToPercent(phase, phase01);
  for (const fn of listeners) fn(percent);
  try {
    ensureChannel()?.postMessage({ type: 'gate-progress', percent });
  } catch {
    /* ponytail: BC optional */
  }
}

export function reportDownloadBytes(loaded: number, total: number): void {
  if (total > 0) {
    reportGatePhase('download', loaded / total);
    return;
  }
  reportGatePhase('download', 0.12);
}

export function subscribeGateProgress(fn: Listener): () => void {
  listeners.add(fn);
  const bc = ensureChannel();
  const onMessage = (event: MessageEvent) => {
    const data = event.data as { type?: string; percent?: number };
    if (data?.type === 'gate-progress' && typeof data.percent === 'number') {
      fn(data.percent);
    }
  };
  bc?.addEventListener('message', onMessage);
  return () => {
    listeners.delete(fn);
    bc?.removeEventListener('message', onMessage);
  };
}

export function resetGateProgressListeners(): void {
  listeners.clear();
  try {
    channel?.close();
  } catch {
    /* ignore */
  }
  channel = null;
}