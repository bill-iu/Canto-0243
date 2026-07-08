import { useEffect, useMemo, useRef, useState } from 'react';

import { BrandLogo, GateInkMeter } from './brand-logo';
import { formatPwaGateLabel } from './gate-label';
import type { OfflineReadinessStatus } from './hooks/useDB.tsx';

const LANDING_SESSION_KEY = 'canto-pwa-gate-landed';
const GATE_BRAND_INTRO_MS = 700;
const LANDING_REVEAL_MS = 420;
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
  onRetry: () => void | Promise<void>;
  onOpenChange: (open: boolean) => void;
  theme?: 'light' | 'dark';
  // For hybrid A+D: detect PWA cold launch to handle iOS airplane home-screen launch gracefully
  isPwaLaunch?: boolean;
  isColdPwaOfflineLaunch?: boolean;
}

export function ReadyGate({
  offlineStatus,
  progress,
  errorMessage,
  isOnline,
  isDbCached,
  isLikelyMetered,
  onRetry,
  onOpenChange,
  theme = 'light',
  isPwaLaunch = false,
  isColdPwaOfflineLaunch = false,
}: ReadyGateProps) {
  const playLanding = useMemo(
    () => !prefersReducedMotion(),
    [],
  );
  const skipGate = useMemo(
    () => offlineStatus === 'ready' && Boolean(sessionStorage.getItem(LANDING_SESSION_KEY)),
    [offlineStatus],
  );

  // D part: for PWA cold offline launch (iOS home screen in airplane), use minimal gate and faster path
  // to avoid relying on perfect SW navigation; still show UI shell via A 's navigateFallback
  const useMinimalForPwa = isPwaLaunch && (isColdPwaOfflineLaunch || !isOnline);
  const effectiveSkip = skipGate || (isPwaLaunch && offlineStatus === 'ready') || isColdPwaOfflineLaunch;
  const shouldShowGate =
    !effectiveSkip &&
    (offlineStatus === 'failed' ||
      (offlineStatus === 'preparing' && Boolean(isDbCached)) ||
      (!isOnline && (offlineStatus === 'not_ready' || Boolean(isDbCached))));

  const [visible, setVisible] = useState(shouldShowGate);
  const [phase, setPhase] = useState<'loading' | 'handoff' | 'exiting' | 'hidden'>(
    shouldShowGate ? 'loading' : 'hidden',
  );
  const handoffStarted = useRef(false);

  useEffect(() => {
    if (shouldShowGate && !visible) {
      handoffStarted.current = false;
      setPhase('loading');
      setVisible(true);
    }
    if (!shouldShowGate && visible && offlineStatus !== 'ready') {
      setPhase('hidden');
      setVisible(false);
    }
  }, [shouldShowGate, visible, offlineStatus]);

  // B: for cold PWA offline launch, force immediate hide of gate
  // so shell reveals right away (even while DB is still loading in background)
  // This prevents getting stuck on the pure launch background color.
  useEffect(() => {
    if (isColdPwaOfflineLaunch && visible) {
      setVisible(false);
      setPhase('hidden');
      onOpenChange(false);
    }
  }, [isColdPwaOfflineLaunch, visible, onOpenChange]);

  useEffect(() => {
    if (offlineStatus === 'preparing') {
      handoffStarted.current = false;
    }
  }, [offlineStatus]);

  useEffect(() => {
    onOpenChange(visible && phase !== 'hidden');
  }, [visible, phase, onOpenChange]);

  useEffect(() => {
    if (isColdPwaOfflineLaunch) return; // B: cold path already handled by the force-hide effect above
    if (offlineStatus !== 'ready' || handoffStarted.current || !visible) return;
    handoffStarted.current = true;

    void (async () => {
      // D: for cold PWA offline launch, skip heavy animation, use minimal + fast handoff
      if (useMinimalForPwa) {
        await sleep(100);
        sessionStorage.setItem(LANDING_SESSION_KEY, '1');
        setPhase('hidden');
        setVisible(false);
        return;
      }
      await awaitGateBrandBeat(playLanding);
      await sleep(320);
      if (playLanding) {
        setPhase('handoff');
        await sleep(280);
      }
      setPhase('exiting');
      await sleep(LANDING_REVEAL_MS);
      sessionStorage.setItem(LANDING_SESSION_KEY, '1');
      setPhase('hidden');
      setVisible(false);
    })();
  }, [offlineStatus, playLanding, visible, useMinimalForPwa, isColdPwaOfflineLaunch]);

  if (!visible || phase === 'hidden') return null;

  const inkProgress =
    offlineStatus === 'ready'
      ? 1
      : offlineStatus === 'preparing'
        ? Math.max(progress / 100, GATE_INK_INDETERMINATE)
        : GATE_INK_INDETERMINATE;

  const label = isColdPwaOfflineLaunch 
    ? 'iOS 飛航冷啟動 - 載入快取內容中'
    : formatPwaGateLabel(offlineStatus, progress, {
        isOnline,
        isDbCached,
        errorMessage,
      });

  const showRetry =
    offlineStatus === 'failed' || (offlineStatus === 'not_ready' && (!isOnline || isDbCached));

  const overlayClass = [
    'preload-overlay',
    (!playLanding || useMinimalForPwa) ? 'preload-overlay--minimal' : '',
    phase === 'exiting' ? 'is-exiting' : '',
    phase === 'handoff' ? 'is-handoff' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={overlayClass} role="status" aria-live="polite" aria-busy={offlineStatus !== 'ready'}>
      <div className="gate-brand">
        <BrandLogo variant="gate" inkProgress={inkProgress} theme={theme} />
      </div>
      <GateInkMeter inkProgress={inkProgress} theme={theme} />
      <p className="gate-status">{label}</p>
      {showRetry && (
        <button type="button" className="primary-button" onClick={() => void onRetry()}>
          重試離線就緒
        </button>
      )}
      {offlineStatus === 'not_ready' && isOnline && !isDbCached && (
        <p className="gate-status" style={{ maxWidth: 'min(420px, 90vw)', fontSize: '0.85rem' }}>
          首次離線就緒需下載較大資料包，建議用 Wi‑Fi。
          {isLikelyMetered ? '（偵測到可能為省流量／慢速網路）' : ''}
        </p>
      )}
    </div>
  );
}
