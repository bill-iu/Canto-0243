import React from 'react';
import { getPortableUpdateCopy } from '../../../shared/portable-update-i18n.mjs';

export type PortableUpdateInfo = {
  available: boolean;
  release_url?: string | null;
  download_hint?: string | null;
  remote?: { tag?: string } | null;
};

type Props = {
  info: PortableUpdateInfo;
  lang: 'zh' | 'zh-Hans' | 'en';
  onDismiss: () => void;
};

export function PortableUpdateBanner({ info, lang, onDismiss }: Props) {
  const tag = info.remote?.tag || '';
  const url = info.release_url || 'https://github.com/bill-iu/Canto-0243/releases/latest';
  const hint = info.download_hint || '';

  const copyHint = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!hint) return;
    try {
      await navigator.clipboard.writeText(hint);
    } catch {
      /* ignore */
    }
  };

  const copy = getPortableUpdateCopy(lang);
  const title = copy.title(tag);
  const openLabel = copy.open;
  const copyLabel = copy.copy;
  const laterLabel = copy.later;

  return (
    <div className="portable-update-banner" role="status">
      <div className="portable-update-banner__text">
        <strong>{title}</strong>
        <span>{copy.sub}</span>
      </div>
      <div className="portable-update-banner__actions">
        <a className="portable-update-banner__btn" href={url} target="_blank" rel="noreferrer">
          {openLabel}
        </a>
        {hint ? (
          <button type="button" className="portable-update-banner__btn" onClick={copyHint}>
            {copyLabel}
          </button>
        ) : null}
        <button
          type="button"
          className="portable-update-banner__close"
          onClick={onDismiss}
          aria-label={laterLabel}
        >
          {laterLabel}
        </button>
      </div>
    </div>
  );
}
