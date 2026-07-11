/** ADR-0032: 閘前進度 + 多 Tab 廣播（F） */

export type GatePhase = 'download' | 'open' | 'validate';

const DOWNLOAD_WEIGHT = 0.85;
const OPEN_WEIGHT = 0.1;
const VALIDATE_WEIGHT = 0.05;

const CHANNEL = 'canto-lexicon-gate-progress';

type Listener = (percent: number) => void;

const listeners = new Set<Listener>();
let channel: BroadcastChannel | null = null;
/** 單次 init 內墨水只進唔退（開庫降級／階段重報唔縮返）。 */
let highWaterPercent = 0;

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

function applyPercent(raw: number, broadcast: boolean): void {
  const percent = Math.max(highWaterPercent, Math.max(0, Math.min(100, raw)));
  highWaterPercent = percent;
  for (const fn of listeners) fn(percent);
  if (!broadcast) return;
  try {
    ensureChannel()?.postMessage({ type: 'gate-progress', percent });
  } catch {
    /* ponytail: BC optional */
  }
}

/** 新一輪閘前 init／重試前清高水位。 */
export function resetGateProgress(): void {
  highWaterPercent = 0;
}

export function reportGatePhase(phase: GatePhase, phase01: number): void {
  applyPercent(phaseToPercent(phase, phase01), true);
}

export function reportDownloadBytes(loaded: number, total: number): void {
  if (total > 0) {
    reportGatePhase('download', loaded / total);
    return;
  }
  // Unknown Content-Length: log-scale advance so UI doesn't stick at ~12% forever
  // (still caps under 0.92 until download phase ends explicitly).
  if (loaded <= 0) {
    reportGatePhase('download', 0.05);
    return;
  }
  const soft = Math.min(0.92, 0.12 + Math.log10(loaded + 10) / 8);
  reportGatePhase('download', soft);
}

export function subscribeGateProgress(fn: Listener): () => void {
  listeners.add(fn);
  const bc = ensureChannel();
  const onMessage = (event: MessageEvent) => {
    const data = event.data as { type?: string; percent?: number };
    if (data?.type === 'gate-progress' && typeof data.percent === 'number') {
      applyPercent(data.percent, false);
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
  highWaterPercent = 0;
  try {
    channel?.close();
  } catch {
    /* ignore */
  }
  channel = null;
}
