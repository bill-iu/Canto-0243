import { getGuideQuick } from '../../shared/guide-i18n.mjs';
import { getHeaderCopy } from '../../shared/header-i18n.mjs';
import type { GuideLang, GuideMode } from './guide-examples';

export interface GuideQuickProps {
  lang: GuideLang;
  disabled?: boolean;
  onPick: (query: string, mode: GuideMode) => void;
  onOpenFullGuide: () => void;
}

function GuideQuickExampleButton({
  label,
  query,
  mode,
  disabled,
  onPick,
}: {
  label: string;
  query: string;
  mode: GuideMode;
  disabled: boolean;
  onPick: (query: string, mode: GuideMode) => void;
}) {
  return (
    <button
      type="button"
      className="guide-quick__example"
      disabled={disabled}
      title={label}
      onClick={() => onPick(query, mode)}
    >
      <code translate="no">{query}</code>
      <span>{label}</span>
    </button>
  );
}

function GuideQuickRowBlock({
  keys,
  title,
  blurb,
  examples,
  disabled,
  onPick,
  inColumn = false,
}: {
  keys: string[];
  title: string;
  blurb: string;
  examples: Array<{ query: string; mode: string; label: string }>;
  disabled: boolean;
  onPick: (query: string, mode: GuideMode) => void;
  inColumn?: boolean;
}) {
  const Tag = inColumn ? 'div' : 'li';
  return (
    <Tag className={`guide-quick__row${inColumn ? ' guide-quick__row--in-column' : ''}`}>
      <div className="guide-quick__keys" aria-hidden>
        {keys.map((key) => (
          <span key={key} className="guide-quick__key">
            {key}
          </span>
        ))}
      </div>
      <div className="guide-quick__body">
        <h3>{title}</h3>
        <p>{blurb}</p>
        <div className="guide-quick__examples">
          {examples.map((ex) => (
            <GuideQuickExampleButton
              key={`${ex.query}-${ex.mode}`}
              query={ex.query}
              mode={ex.mode as GuideMode}
              label={ex.label}
              disabled={disabled}
              onPick={onPick}
            />
          ))}
        </div>
      </div>
    </Tag>
  );
}

export function GuideQuick({ lang, disabled = false, onPick, onOpenFullGuide }: GuideQuickProps) {
  const copy = getGuideQuick(lang);
  const heroTitle = getHeaderCopy(lang).title;
  return (
    <section className="guide-quick" aria-labelledby="guideQuickTitle">
      <header className="guide-quick__header">
        <div className="guide-quick__title-row">
          <h2 id="guideQuickTitle">{copy.title}</h2>
          {/* Narrow only (CSS): brand title between 教你點用 / 完整說明; wide keeps app-bar hero */}
          <p className="guide-quick__hero" aria-hidden="true">
            {heroTitle}
          </p>
          <button type="button" className="ghost-button guide-quick__cta" onClick={onOpenFullGuide}>
            {copy.cta}
          </button>
        </div>
      </header>
      <ul className="guide-quick__rows">
        {copy.rows.map((row) => (
          <GuideQuickRowBlock
            key={row.keys.join(',')}
            keys={row.keys}
            title={row.title}
            blurb={row.blurb}
            examples={row.examples}
            disabled={disabled}
            onPick={onPick}
          />
        ))}
      </ul>
      <div className="guide-quick__columns">
        {copy.columns.map((col, colIdx) => (
          <div key={colIdx} className="guide-quick__column">
            {col.rows.map((row) => (
              <GuideQuickRowBlock
                key={row.title}
                keys={row.keys}
                title={row.title}
                blurb={row.blurb}
                examples={row.examples}
                disabled={disabled}
                onPick={onPick}
                inColumn
              />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
