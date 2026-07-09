import { useEffect, useRef, useState } from 'react';

const GATE_INK_CLIP_MAX = 200;
const WARMUP_DONE_HOLD_MS = 1200;
const WARMUP_DONE_FADE_MS = 420;

type Props = {
  tailProgress: number;
  startupComplete: boolean;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'en';
};

export function TailPreloadBadge({ tailProgress, startupComplete, theme = 'light', lang = 'zh' }: Props) {
  const [visible, setVisible] = useState(false);
  const [done, setDone] = useState(false);
  const [exiting, setExiting] = useState(false);
  const shownRef = useRef(false);
  const dismissTimer = useRef<number | null>(null);

  useEffect(() => {
    if (startupComplete && shownRef.current) {
      setDone(true);
      if (dismissTimer.current) window.clearTimeout(dismissTimer.current);
      dismissTimer.current = window.setTimeout(() => {
        setExiting(true);
        dismissTimer.current = window.setTimeout(() => {
          setVisible(false);
          setDone(false);
          setExiting(false);
          shownRef.current = false;
        }, WARMUP_DONE_FADE_MS);
      }, WARMUP_DONE_HOLD_MS);
      return;
    }
    if (!startupComplete && tailProgress > 0 && tailProgress < 100) {
      shownRef.current = true;
      setVisible(true);
      setDone(false);
      setExiting(false);
    }
    return () => {
      if (dismissTimer.current) window.clearTimeout(dismissTimer.current);
    };
  }, [startupComplete, tailProgress]);

  if (!visible) return null;

  const progress01 = Math.max(0, Math.min(1, tailProgress / 100));
  const inkW = (progress01 * GATE_INK_CLIP_MAX).toFixed(1);
  const label = done
    ? lang === 'en'
      ? 'Ready!'
      : '搞掂！'
    : lang === 'en'
      ? 'Finishing up'
      : '執埋啲手尾';

  return (
    <div
      className={`warmup-badge${done ? ' is-done' : ''}${exiting ? ' is-exiting' : ''}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-label={done ? (lang === 'en' ? 'Background preload complete' : '背景預載完成') : `${label} ${Math.round(tailProgress)}%`}
    >
      <span className="warmup-badge__label">{label}</span>
      <svg className="warmup-badge__ink" xmlns="http://www.w3.org/2000/svg" viewBox="0 38 200 34" aria-hidden="true" focusable="false">
        <defs>
          <clipPath id="pwa-warmup-ink-clip">
            <rect className="warmup-badge__ink-clip" x="0" y="38" width={inkW} height="34" />
          </clipPath>
        </defs>
        <g className="warmup-badge__ink-track" aria-hidden="true">
          <use href="#brand-ink-blob" fill="currentColor" />
          <use href="#brand-ink-flicks-current" />
        </g>
        <g className="warmup-badge__ink-fill" clipPath="url(#pwa-warmup-ink-clip)" aria-hidden="true">
          <use href="#brand-ink-blob" fill="currentColor" />
          <use href="#brand-ink-flicks-current" />
        </g>
      </svg>
      {!done && <span className="warmup-badge__pct">{Math.round(tailProgress)}%</span>}
    </div>
  );
}