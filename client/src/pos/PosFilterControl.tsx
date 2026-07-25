import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import './pos-filter.css';

import {
  posFilterActiveCount,
  resetPosFilter,
  togglePosFilterValue,
  type PosFilterState,
} from './filter.ts';
import type { FormalPos, PosFamily, PosVoice } from './types.ts';
import { getPosFilterCopy } from '../../../shared/pos-filter-i18n.mjs';

type Props = {
  value: PosFilterState;
  onChange: (next: PosFilterState) => void;
  lang?: 'zh' | 'zh-Hans' | 'en';
  disabled?: boolean;
};

const POS: FormalPos[] = ['n', 'v', 'a', 'r', 'x'];
const FAMILY: PosFamily[] = ['idiom', 'chengyu', 'suyu', 'yanyu', 'xiehouyu'];
const VOICE: PosVoice[] = ['active', 'passive'];

function FilterIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 6h16l-6.3 7.1V18l-3.4 1.7v-6.6z" /></svg>;
}

export function PosFilterControl({ value, onChange, lang = 'zh', disabled = false }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const count = posFilterActiveCount(value);
  const copy = getPosFilterCopy(lang);
  const label = copy.label;

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    const trigger = triggerRef.current;
    document.body.style.overflow = 'hidden';
    const focusable = () => [...(panelRef.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ) ?? [])];
    requestAnimationFrame(() => (focusable()[0] ?? panelRef.current)?.focus());
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setOpen(false);
        return;
      }
      if (event.key !== 'Tab') return;
      const items = focusable();
      if (!items.length) return;
      const first = items[0]!;
      const last = items[items.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (rootRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('pointerdown', onPointerDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('pointerdown', onPointerDown);
      trigger?.focus();
    };
  }, [open]);

  const axis = <T extends FormalPos | PosFamily | PosVoice>(
    key: 'pos' | 'family' | 'voice',
    choices: T[],
  ) => (
    <fieldset className="pos-filter__axis">
      <legend>{copy.axes[key].title}</legend>
      <div className="pos-filter__chips">
        {choices.map((item) => {
          const selected = (value[key] as string[]).includes(item);
          return <button
            key={item}
            type="button"
            className={`pos-filter__chip${selected ? ' is-selected' : ''}`}
            aria-pressed={selected}
            onClick={() => onChange(togglePosFilterValue(value, key as never, item as never))}
          >{(copy.axes[key].choices as Record<string, string>)[String(item)]}</button>;
        })}
      </div>
    </fieldset>
  );

  return (
    <div className="pos-filter" ref={rootRef}>
      <button
        ref={triggerRef}
        type="button"
        className={`pos-filter__trigger${count ? ' is-active' : ''}`}
        aria-label={label}
        aria-expanded={open}
        aria-controls="posFilterPanel"
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
      >
        <FilterIcon />
        <span className="pos-filter__trigger-label-full">{label}</span>
        <span className="pos-filter__trigger-label-short">{copy.shortLabel}</span>
        {count ? <b aria-label={`${count}`}>{count}</b> : null}
      </button>
      {open ? createPortal(<>
        <button className="pos-filter__scrim" type="button" aria-label={copy.closeFilters} onClick={() => setOpen(false)} />
        <section
          ref={panelRef}
          id="posFilterPanel"
          className="pos-filter__panel"
          role="dialog"
          aria-modal="true"
          aria-label={label}
          tabIndex={-1}
        >
          <header><div><p>{copy.heading}</p><h2>{label}</h2></div><button type="button" onClick={() => setOpen(false)} aria-label={copy.close}>×</button></header>
          {axis('pos', POS)}
          {axis('family', FAMILY)}
          {axis('voice', VOICE)}
          <footer>
            <span>{copy.withinAcross}</span>
            <button type="button" disabled={!count} onClick={() => onChange(resetPosFilter())}>{copy.reset}</button>
          </footer>
        </section>
      </>, document.body) : null}
    </div>
  );
}
