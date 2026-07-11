import { useEffect, useRef, useState } from 'react';

const WARMUP_DONE_HOLD_MS = 700;
const WARMUP_DONE_FADE_MS = 420;

type Props = {
  tailProgress: number;
  startupComplete: boolean;
  theme?: 'light' | 'dark';
  lang?: 'zh' | 'en';
};

export function TailPreloadBadge({ tailProgress, startupComplete, lang = 'zh' }: Props) {
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

  const label = done
    ? lang === 'en'
      ? 'Done!'
      : '完成！'
    : lang === 'en'
      ? 'Loading…'
      : '載入中…';

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
