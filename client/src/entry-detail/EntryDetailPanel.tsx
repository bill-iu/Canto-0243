import { useCallback, useEffect, useState } from 'react';
import { tDetail } from '../../../shared/entry-detail-i18n.mjs';
import { pickPreferredReadingIndex } from '../../../shared/entry-detail-core.mjs';
import type { EntryDetailModel } from './types.ts';

export function EntryDetailPanel({
  literal,
  model,
  loading,
  relationsLoading,
  lang,
  preferredJyutping,
  onClose,
  onRelationPick,
  onPutInWorkbench,
}: {
  literal: string;
  model: EntryDetailModel | null;
  loading?: boolean;
  relationsLoading?: boolean;
  lang: 'zh' | 'en';
  preferredJyutping?: string | null;
  onClose: () => void;
  onRelationPick: (literal: string) => void;
  onPutInWorkbench?: (literal: string) => void;
}) {
  const [readingIdx, setReadingIdx] = useState(0);
  const reading = model?.readings[readingIdx] ?? model?.readings[0];

  useEffect(() => {
    if (!model) return;
    setReadingIdx(pickPreferredReadingIndex(model.readings, preferredJyutping ?? undefined));
  }, [model, preferredJyutping]);
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(literal);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ponytail: clipboard optional */
    }
  }, [literal]);

  const initialsText = reading?.initials.filter(Boolean).join(' ') || '—';
  const finalsText = reading?.finals.filter(Boolean).join(' ') || '—';
  const loadingLabel = lang === 'en' ? 'Loading…' : '載入中…';

  return (
    <aside className="entry-detail-panel" aria-label={tDetail('detail.title', lang)}>
      <header className="entry-detail-panel__header">
        <h2 className="entry-detail-panel__title">{tDetail('detail.title', lang)}</h2>
        <button
          type="button"
          className="entry-detail-panel__close"
          onClick={onClose}
          aria-label={tDetail('detail.close', lang)}
        >
          ×
        </button>
      </header>
      <div className="entry-detail-panel__body">
        <div className="entry-detail-panel__hero">
          <div className="entry-detail-panel__literal">{literal}</div>
          <div className="entry-detail-panel__actions">
            <button type="button" className="entry-detail-panel__icon-btn" onClick={() => void handleCopy()}>
              {copied ? tDetail('detail.copy.done', lang) : tDetail('detail.copy', lang)}
            </button>
            {onPutInWorkbench ? (
              <button type="button" className="entry-detail-panel__icon-btn" onClick={() => onPutInWorkbench(literal)}>
                {lang === 'zh' ? '放入句格' : 'Put in workbench'}
              </button>
            ) : null}
          </div>
        </div>

        {loading || !model || !reading ? (
          <p className="entry-detail-panel__loading" aria-live="polite">
            {loadingLabel}
          </p>
        ) : (
          <>
            <p className="entry-detail-panel__jyutping">{reading.jyutping}</p>
            <span className="entry-detail-panel__code-pill">{reading.code0243}</span>

            {model.readings.length > 1 ? (
              <div className="entry-detail-reading-tabs" role="tablist">
                {model.readings.map((item, index) => (
                  <button
                    key={`${item.jyutping}-${index}`}
                    type="button"
                    role="tab"
                    className={`entry-detail-reading-tab${index === readingIdx ? ' is-active' : ''}`}
                    aria-selected={index === readingIdx}
                    onClick={() => setReadingIdx(index)}
                  >
                    {tDetail('detail.reading', lang, { n: index + 1 })}
                  </button>
                ))}
              </div>
            ) : null}

            <section className="entry-detail-section">
              <h3 className="entry-detail-section__title">{tDetail('detail.phonetic', lang)}</h3>
              <div className="entry-detail-phonetic-grid">
                <div className="entry-detail-phonetic-card">
                  <span className="entry-detail-phonetic-card__label">{tDetail('detail.initials', lang)}</span>
                  <span className="entry-detail-phonetic-card__value">{initialsText}</span>
                </div>
                <div className="entry-detail-phonetic-card">
                  <span className="entry-detail-phonetic-card__label">{tDetail('detail.finals', lang)}</span>
                  <span className="entry-detail-phonetic-card__value">{finalsText}</span>
                </div>
              </div>
            </section>

            <section className="entry-detail-section">
              <h3 className="entry-detail-section__title">{tDetail('detail.tone', lang)}</h3>
              <div className="entry-detail-tone-rows">
                <div className="entry-detail-tone-row">
                  <span>{tDetail('detail.tone.0243', lang)}</span>
                  <strong>{reading.code0243}</strong>
                </div>
                <div className="entry-detail-tone-row">
                  <span>{tDetail('detail.tone.02493', lang)}</span>
                  <strong>{reading.code02493}</strong>
                </div>
              </div>
            </section>

            <div className="entry-detail-meta-row">
              <span>{tDetail('detail.length', lang)}</span>
              <strong>{model.length}</strong>
            </div>
            <div className="entry-detail-meta-row">
              <span>{tDetail('detail.corpusWeight', lang)}</span>
              <strong>{model.corpusWeight.toLocaleString()}</strong>
            </div>

            {model.posChips && model.posChips.length ? (
              <section className="entry-detail-section">
                <h3 className="entry-detail-section__title">{tDetail('detail.pos', lang)}</h3>
                <div className="entry-detail-chip-row">
                  {model.posChips.map((chip) => (
                    <span key={chip} className="entry-detail-source-tag">
                      {chip}
                    </span>
                  ))}
                </div>
              </section>
            ) : null}

            <section className="entry-detail-section">
              <h3 className="entry-detail-section__title">{tDetail('detail.sources', lang)}</h3>
              {model.sources.length ? (
                model.sources.map((src) => (
                  <span key={src} className="entry-detail-source-tag">
                    {src}
                  </span>
                ))
              ) : (
                <span className="entry-detail-source-tag">{tDetail('detail.noSources', lang)}</span>
              )}
            </section>

            {relationsLoading ? (
              <>
                <section className="entry-detail-section">
                  <h3 className="entry-detail-section__title">{tDetail('detail.syns', lang)}</h3>
                  <p className="entry-detail-panel__loading">{loadingLabel}</p>
                </section>
                <section className="entry-detail-section">
                  <h3 className="entry-detail-section__title">{tDetail('detail.ants', lang)}</h3>
                  <p className="entry-detail-panel__loading">{loadingLabel}</p>
                </section>
              </>
            ) : (
              <>
                {model.syns.length ? (
                  <section className="entry-detail-section">
                    <h3 className="entry-detail-section__title">{tDetail('detail.syns', lang)}</h3>
                    <div className="entry-detail-chip-row">
                      {model.syns.map((word) => (
                        <button
                          key={word}
                          type="button"
                          className="entry-detail-chip"
                          onClick={() => onRelationPick(word)}
                        >
                          {word}
                        </button>
                      ))}
                    </div>
                  </section>
                ) : null}

                {model.ants.length ? (
                  <section className="entry-detail-section">
                    <h3 className="entry-detail-section__title">{tDetail('detail.ants', lang)}</h3>
                    <div className="entry-detail-chip-row">
                      {model.ants.map((word) => (
                        <button
                          key={word}
                          type="button"
                          className="entry-detail-chip"
                          onClick={() => onRelationPick(word)}
                        >
                          {word}
                        </button>
                      ))}
                    </div>
                  </section>
                ) : null}
              </>
            )}
          </>
        )}
      </div>
    </aside>
  );
}