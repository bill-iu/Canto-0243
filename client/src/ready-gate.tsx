import { useEffect, useMemo, useRef, useState } from 'react';

import { BrandLogo, GateInkMeter } from './brand-logo';
import { formatPwaGateLabel } from './gate-label';
import type { OfflineReadinessStatus } from './hooks/useDB.tsx';
import {
  hasPwaGateLanded,
  PWA_GATE_LANDED_KEY,
  revealPwaShell,
} from './pwa-shell-boot';

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
  suppressGateOverlay?: boolean;
  onRetry: () => void | Promise<void>;
  onOpenChange: (open: boolean) => void;
  theme?: 'light' | 'dark';
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
  // 冷啓 full landing；熱啓／cached 用 minimal 但仍顯示 logo+ink
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

  // 熱啓重開：session 已 landed 仍可喺 preparing 顯示 minimal 閘
  const [visible, setVisible] = useState(true);
  const [phase, setPhase] = useState<'loading' | 'handoff' | 'exiting' | 'hidden'>('loading');
  const handoffStarted = useRef(false);

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
      handoffStarted.current = false;
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
      handoffStarted.current = false;
    }
  }, [offlineStatus]);

  useEffect(() => {
    if (!suppressGateOverlay || offlineStatus !== 'ready') return;
    handoffStarted.current = true;
    sessionStorage.setItem(PWA_GATE_LANDED_KEY, '1');
    revealPwaShell();
    setPhase('hidden');
    setVisible(false);
  }, [suppressGateOverlay, offlineStatus]);

  useEffect(() => {
    onOpenChange(visible && phase !== 'hidden');
  }, [visible, phase, onOpenChange]);

  useEffect(() => {
    if (offlineStatus !== 'ready' || handoffStarted.current || !visible) return;
    handoffStarted.current = true;

    void (async () => {
      if (skipOverlay) {
        sessionStorage.setItem(PWA_GATE_LANDED_KEY, '1');
        revealPwaShell();
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
      sessionStorage.setItem(PWA_GATE_LANDED_KEY, '1');
      revealPwaShell();
      setPhase('hidden');
      setVisible(false);
    })();
  }, [offlineStatus, playLanding, visible, skipOverlay]);

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
    // 熱啓／已 landed session：minimal（短儀式）但 CSS 仍顯示 logo+ink
    !playLanding || isDbCached || hasPwaGateLanded() ? 'preload-overlay--minimal' : '',
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