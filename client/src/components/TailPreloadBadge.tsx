import { useEffect, useRef, useState } from 'react';
import { getWarmupCopy } from '../../../shared/warmup-i18n.mjs';

const WARMUP_DONE_HOLD_MS = 700;
const WARMUP_DONE_FADE_MS = 420;

type Props = {
  tailProgress: number;
  startupComplete: boolean;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'zh-Hans' | 'en';
  /** Fires after badge fully hidden (or when tail skipped / already complete). */
  onDismiss?: () => void;
};

export function TailPreloadBadge({ tailProgress, startupComplete, lang = 'zh', onDismiss }: Props) {
  const [visible, setVisible] = useState(false);
  const [done, setDone] = useState(false);
  const [exiting, setExiting] = useState(false);
  const shownRef = useRef(false);
  const dismissTimer = useRef<number | null>(null);
  const dismissedRef = useRef(false);
  const onDismissRef = useRef(onDismiss);
  onDismissRef.current = onDismiss;

  const fireDismiss = () => {
    if (dismissedRef.current) return;
    dismissedRef.current = true;
    onDismissRef.current?.();
  };

  useEffect(() => {
    if (startupComplete && !shownRef.current) {
      fireDismiss();
      return;
    }
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
          fireDismiss();
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

  const copy = getWarmupCopy(lang);
  const label = done
    ? copy.done
    : copy.loading;

  return (
    <div
      className={`warmup-badge${done ? ' is-done' : ''}${exiting ? ' is-exiting' : ''}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      aria-label={label}
    >
      <span className="warmup-badge__label">{label}</span>
    </div>
  );
}
