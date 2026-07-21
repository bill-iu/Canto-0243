/**
 * Desktop (portable host) session lifecycle — ADR-0068.
 * Default: stop server when the last product browser tab closes; reload is safe
 * via delayed /shutdown + cancel on load.
 */

import { isPortableHost } from './host-mode.ts';

const TABS_KEY = 'canto-desktop-tabs-v1';
const SETTING_KEY = 'canto-desktop-stop-on-last-tab-v1';
const CHANNEL = 'canto-desktop-session-v1';
const HEARTBEAT_MS = 2000;
const STALE_MS = 6000;
const SHUTDOWN_DELAY_MS = 1600;

export type DesktopStopMode = 'last-tab' | 'keep-alive';

type TabRecord = { id: string; ts: number };

function readTabs(): TabRecord[] {
  try {
    const raw = localStorage.getItem(TABS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as TabRecord[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeTabs(tabs: TabRecord[]): void {
  try {
    localStorage.setItem(TABS_KEY, JSON.stringify(tabs));
  } catch {
    /* ignore quota */
  }
}

/** Default true = stop when last browser tab closes (grill On+safe reload). */
export function isStopOnLastTabEnabled(): boolean {
  try {
    const v = localStorage.getItem(SETTING_KEY);
    if (v === null) return true;
    return v === '1' || v === 'true';
  } catch {
    return true;
  }
}

export function setStopOnLastTabEnabled(on: boolean): void {
  try {
    localStorage.setItem(SETTING_KEY, on ? '1' : '0');
  } catch {
    /* ignore */
  }
  try {
    window.dispatchEvent(new CustomEvent('canto-desktop-stop-mode', { detail: { on } }));
  } catch {
    /* ignore */
  }
}

export function getDesktopStopMode(): DesktopStopMode {
  return isStopOnLastTabEnabled() ? 'last-tab' : 'keep-alive';
}

/** Show explicit menu stop when keep-alive (last-tab stop OFF). */
export function shouldShowDesktopExitMenu(): boolean {
  return isPortableHost() && !isStopOnLastTabEnabled();
}

function prune(tabs: TabRecord[], now: number, selfId?: string): TabRecord[] {
  return tabs.filter((t) => now - t.ts < STALE_MS && t.id !== selfId);
}

function scheduleShutdown(): void {
  const body = JSON.stringify({ delay_ms: SHUTDOWN_DELAY_MS });
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      if (navigator.sendBeacon('/shutdown', blob)) return;
    }
  } catch {
    /* fall through */
  }
  try {
    void fetch('/shutdown', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    });
  } catch {
    /* ignore */
  }
}

function cancelShutdown(): void {
  try {
    void fetch('/shutdown/cancel', { method: 'POST', keepalive: true });
  } catch {
    /* ignore */
  }
}

let installed = false;

/** Call once on portable host boot (main.tsx). */
export function installDesktopSessionLifecycle(): void {
  if (!isPortableHost() || installed || typeof window === 'undefined') return;
  installed = true;

  const tabId =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID()
      : `t-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

  const touch = () => {
    const now = Date.now();
    const others = prune(readTabs(), now, tabId);
    others.push({ id: tabId, ts: now });
    writeTabs(others);
  };

  touch();
  cancelShutdown();

  const beat = window.setInterval(touch, HEARTBEAT_MS);

  let channel: BroadcastChannel | null = null;
  try {
    channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = (ev) => {
      if (ev.data?.type === 'ping') touch();
    };
  } catch {
    channel = null;
  }

  const onHide = (event: PageTransitionEvent) => {
    if (event.persisted) return;
    window.clearInterval(beat);
    const now = Date.now();
    const remaining = prune(readTabs(), now, tabId);
    writeTabs(remaining);
    try {
      channel?.postMessage({ type: 'leave', id: tabId });
    } catch {
      /* ignore */
    }
    if (remaining.length === 0 && isStopOnLastTabEnabled()) {
      scheduleShutdown();
    }
  };

  window.addEventListener('pagehide', onHide);
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      touch();
      cancelShutdown();
    }
  });
}
