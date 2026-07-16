/**
 * Portable host: poll GET /ready until gate_ready (ADR-0055).
 */
import { useEffect, useState } from 'react';

const POLL_MS = 500;

/** Flat readiness snapshot from app.startup.readiness_gate.snapshot */
export interface ReadySnapshot {
  gate_ready: boolean;
  db_ready?: boolean;
  degraded?: boolean;
  status?: string;
  progress?: number;
  tail_progress?: number;
  startup_complete?: boolean;
  ready?: boolean;
  error?: string | null;
  [key: string]: unknown;
}

export interface UsePortableReadyReturn {
  isReady: boolean;
  snapshot: ReadySnapshot | null;
  error: Error | null;
}

export function usePortableReady(enabled = true): UsePortableReadyReturn {
  const [snapshot, setSnapshot] = useState<ReadySnapshot | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled) return;

    let cancelled = false;

    const poll = async () => {
      try {
        const res = await fetch('/ready', { cache: 'no-store' });
        if (!res.ok) throw new Error(`ready ${res.status}`);
        const data = (await res.json()) as ReadySnapshot;
        if (cancelled) return;
        setSnapshot(data);
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err : new Error(String(err)));
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [enabled]);

  return {
    isReady: Boolean(snapshot?.gate_ready),
    snapshot: enabled ? snapshot : null,
    error: enabled ? error : null,
  };
}
