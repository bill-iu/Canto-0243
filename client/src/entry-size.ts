/**
 * 字體大小檔（小／中／大）— 全域縮放倍率，影響主查詢詞條與句格工作台候選卡。
 * 窄屏 <768px：0.8／1.0／1.25；寬屏 ≥768px：1.0／1.25／1.5。預設 medium。
 * CSS 讀 `--entry-scale`（見 shared/open-design.css）；本文 localStorage 與 React state 同步。
 */
import { useCallback, useEffect, useState } from 'react';

export type EntrySize = 'small' | 'medium' | 'large';

const KEY = 'canto-entry-size';
const EVT = 'canto-entry-size-change';
const VALID: ReadonlySet<EntrySize> = new Set(['small', 'medium', 'large']);

function isEntrySize(v: unknown): v is EntrySize {
  return typeof v === 'string' && VALID.has(v as EntrySize);
}

function read(): EntrySize {
  try {
    const v = localStorage.getItem(KEY);
    return isEntrySize(v) ? v : 'medium';
  } catch {
    return 'medium';
  }
}

function apply(size: EntrySize): void {
  try {
    document.documentElement.dataset.entrySize = size;
  } catch {
    /* ignore */
  }
}

export function getEntrySize(): EntrySize {
  return read();
}

export function setEntrySize(size: EntrySize): void {
  try {
    localStorage.setItem(KEY, size);
  } catch {
    /* ignore quota */
  }
  apply(size);
  try {
    window.dispatchEvent(new CustomEvent(EVT, { detail: { size } }));
  } catch {
    /* ignore */
  }
}

/** Boot：React mount 前套用 data-attr，避免檔位閃爍（ponytail：base CSS 已係 medium，零 FOUC）。 */
export function applyBootEntrySizeFromStorage(): void {
  apply(read());
}

/** 跨 mount 同步（App 與 WorkbenchPage 各自用同一份 localStorage）。 */
export function useEntrySize(): [EntrySize, (next: EntrySize) => void] {
  const [size, setSize] = useState<EntrySize>(read);
  useEffect(() => {
    const onChange = () => setSize(read());
    window.addEventListener(EVT, onChange);
    window.addEventListener('storage', onChange);
    return () => {
      window.removeEventListener(EVT, onChange);
      window.removeEventListener('storage', onChange);
    };
  }, []);
  const update = useCallback((next: EntrySize) => setEntrySize(next), []);
  return [size, update];
}