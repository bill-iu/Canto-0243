import { useEffect, useMemo, useRef, useState } from 'react';

import { BrandLogo } from './brand-logo';
import { formatPwaGateLabel } from './gate-label';
import type { OfflineReadinessStatus } from './hooks/db-context.ts';
import {
  hasPwaGateLanded,
  PWA_GATE_LANDED_KEY,
  revealPwaShell,
} from './pwa-shell-boot';

/** Cold-start brand beat (fonts) — only while still loading, not after ready. */
const GATE_BRAND_INTRO_MS = 700;
/** Short cold-start fade after ready (CONTEXT: 就緒閘解鎖即露殼). */
const COLD_FADE_MS = 180;
const GATE_INK_INDETERMINATE = 0.12;

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

async function awaitGateBrandBeat(playLanding: boolean) {
  if (!playLanding) return;
  try {
    if (document.fonts?.ready) {
      await Promise.race([document.fonts.ready, sleep(2400)]);
    }
  } catch {
    /* timeout fallback below */
  }
  if (!document.documentElement.classList.contains('fonts-ready')) {
    document.documentElement.classList.add('fonts-ready');
    (window as Window & { __gateBrandShownAt?: number }).__gateBrandShownAt = performance.now();
  }
  const shownAt =
    (window as Window & { __gateBrandShownAt?: number }).__gateBrandShownAt ?? performance.now();
  const remain = GATE_BRAND_INTRO_MS - (performance.now() - shownAt);
  if (remain > 0) await sleep(remain);
}

export interface ReadyGateProps {
  offlineStatus: OfflineReadinessStatus;
  progress: number;
  errorMessage?: string;
  isOnline: boolean;
  isDbCached: boolean | null;
  isLikelyMetered: boolean;
  suppressGateOverlay?: boolean;
  onRetry: () => void | Promise<void>;
  /** true while gate blocks search (not ready). false as soon as ready — shell must not wait for fade. */
  onOpenChange: (open: boolean) => void;
  theme?: 'light' | 'dark';
}

function unlockShell() {
  sessionStorage.setItem(PWA_GATE_LANDED_KEY, '1');
  revealPwaShell();
}

export function ReadyGate({
  offlineStatus,
  progress,
  errorMessage,
  isOnline,
  isDbCached,
  isLikelyMetered,
  suppressGateOverlay = false,
  onRetry,
  onOpenChange,
  theme = 'light',
}: ReadyGateProps) {
  // 冷啓 full landing；熱啓／cached 用 minimal
  const playLanding = useMemo(
    () => !prefersReducedMotion() && !hasPwaGateLanded() && !isDbCached,
    [isDbCached],
  );
  const skipOverlay = useMemo(() => hasPwaGateLanded(), []);

  // preparing／not_ready／failed 一律顯示閘（含熱啓）；suppress 只用於 ready 後即時收起
  const shouldShowGate =
    !suppressGateOverlay &&
    (offlineStatus === 'failed' ||
      offlineStatus === 'preparing' ||
      offlineStatus === 'not_ready');

  const [visible, setVisible] = useState(true);
  const [phase, setPhase] = useState<'loading' | 'exiting' | 'hidden'>('loading');
  const unlockStarted = useRef(false);

  // Shell / search gating: only while not ready (not during fade).
  useEffect(() => {
    if (offlineStatus === 'ready' || suppressGateOverlay) {
      onOpenChange(false);
    } else if (shouldShowGate) {
      onOpenChange(true);
    }
  }, [offlineStatus, shouldShowGate, suppressGateOverlay, onOpenChange]);

  useEffect(() => {
    if (!visible || phase === 'hidden') return;
    let cancelled = false;
    const handoff = () => {
      if (!cancelled) document.getElementById('pwaBootGate')?.remove();
    };
    requestAnimationFrame(() => requestAnimationFrame(handoff));
    return () => {
      cancelled = true;
    };
  }, [visible, phase]);

  useEffect(() => {
    if (shouldShowGate && !visible) {
      unlockStarted.current = false;
      setPhase('loading');
      setVisible(true);
    }
    if (!shouldShowGate && visible && offlineStatus !== 'ready') {
      setPhase('hidden');
      setVisible(false);
    }
  }, [shouldShowGate, visible, offlineStatus]);

  useEffect(() => {
    if (offlineStatus === 'preparing') {
      unlockStarted.current = false;
    }
  }, [offlineStatus]);

  // suppress + ready: instant
  useEffect(() => {
    if (!suppressGateOverlay || offlineStatus !== 'ready') return;
    unlockStarted.current = true;
    unlockShell();
    setPhase('hidden');
    setVisible(false);
  }, [suppressGateOverlay, offlineStatus]);

  // ready: unlock shell immediately; optional short cold fade only
  useEffect(() => {
    if (offlineStatus !== 'ready' || unlockStarted.current || !visible) return;
    unlockStarted.current = true;

    // Always unlock shell + boot DOM now (CONTEXT: 就緒閘解鎖即露殼).
    unlockShell();

    void (async () => {
      // 熱啓／已 landed／cached / reduced-motion：零延遲拆 overlay
      if (skipOverlay || !playLanding || prefersReducedMotion()) {
        setPhase('hidden');
        setVisible(false);
        return;
      }
      // 冷啓：短 fade 後拆（殼已可交互）
      setPhase('exiting');
      await sleep(COLD_FADE_MS);
      setPhase('hidden');
      setVisible(false);
    })();
  }, [offlineStatus, playLanding, visible, skipOverlay]);

  // Brand beat only while still loading (not after ready blocks shell).
  useEffect(() => {
    if (offlineStatus === 'ready' || !playLanding || !visible) return;
    void awaitGateBrandBeat(true);
  }, [offlineStatus, playLanding, visible]);

  if (!visible || phase === 'hidden') return null;

  const inkProgress =
    offlineStatus === 'ready'
      ? 1
      : offlineStatus === 'preparing'
        ? Math.max(progress / 100, GATE_INK_INDETERMINATE)
        : GATE_INK_INDETERMINATE;

  const label = formatPwaGateLabel(offlineStatus, progress, {
    isOnline,
    isDbCached,
    errorMessage,
  });

  const showRetry =
    offlineStatus === 'failed' || (offlineStatus === 'not_ready' && (!isOnline || isDbCached));

  const overlayClass = [
    'ready-gate',
    'preload-overlay',
    !playLanding || isDbCached || hasPwaGateLanded() ? 'preload-overlay--minimal' : '',
    phase === 'exiting' ? 'is-exiting' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={overlayClass} role="status" aria-live="polite" aria-busy={offlineStatus !== 'ready'}>
      <div className="gate-brand">
        <BrandLogo variant="gate" inkProgress={inkProgress} theme={theme} />
        <p className="gate-status">{label}</p>
      </div>
      {showRetry && (
        <button type="button" className="primary-button" onClick={() => void onRetry()}>
          重試離線就緒
        </button>
      )}
      {offlineStatus === 'not_ready' && isOnline && !isDbCached && (
        <p className="gate-status gate-status--hint">
          首次離線就緒需下載較大資料包，建議用 Wi‑Fi。
          {isLikelyMetered ? '（偵測到可能為省流量／慢速網路）' : ''}
        </p>
      )}
    </div>
  );
}
